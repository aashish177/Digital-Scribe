from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal
from sse_starlette.sse import EventSourceResponse
from graph.workflow import create_content_workflow, initialize_state
from api.summaries import AGENT_ORDER, summarize_node, summarize_run, run_totals
from api.workspaces import router as workspaces_router, get_workspace, drop_orphaned_collections
from vector_stores.chroma import workspace_collection
from config import Config
import json
import logging
import re
import time
import uuid
import sys
import os
import httpx
import asyncio

# Ensure the root project path is available for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_config import setup_logging

app = FastAPI(
    title="Digital Scribe API",
    description="REST API for the Multi-Agent Content Creation Pipeline.",
    version="1.0.0"
)

# The UI is served from this same app, so only local origins need CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(workspaces_router)

# Setup initial configurations
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Compile TWO workflow variants once per worker, both with MemorySaver
# so get_state() works on either to retrieve the full accumulated pipeline state.
workflow_app = create_content_workflow(enable_hitl=False, checkpointer="memory")
workflow_app_hitl = create_content_workflow(enable_hitl=True)

# In-memory store
jobs: Dict[str, Dict[str, Any]] = {}


def forget_job(request_id: str) -> None:
    """Drop a job and its checkpointed run state (chunks, findings, drafts)."""
    jobs.pop(request_id, None)
    for workflow in (workflow_app, workflow_app_hitl):
        try:
            workflow.checkpointer.delete_thread(request_id)
        except Exception as e:
            logger.warning(f"Could not delete run state for {request_id[:8]}: {e}")


def sweep_jobs(now: Optional[float] = None) -> None:
    """Forget finished or abandoned runs once they are older than JOB_TTL_SECONDS."""
    now = now or time.time()
    expired = [rid for rid, j in jobs.items()
               if j["status"] in ("completed", "failed", "awaiting_approval")
               and now - j.get("created_at", now) > Config.JOB_TTL_SECONDS]
    for rid in expired:
        forget_job(rid)


def add_job(request_id: str, job: Dict[str, Any]) -> None:
    """Store a job, dropping expired ones and the oldest finished ones past the cap."""
    sweep_jobs()
    jobs[request_id] = {"created_at": time.time(), **job}
    if len(jobs) > Config.MAX_JOBS_IN_MEMORY:
        finished = [rid for rid, j in jobs.items() if j["status"] in ("completed", "failed")]
        for rid in finished[: len(jobs) - Config.MAX_JOBS_IN_MEMORY]:
            forget_job(rid)


def webhook_allowed(url: Optional[HttpUrl]) -> bool:
    return url is not None and url.scheme == "https" and (url.host or "").lower() in Config.WEBHOOK_ALLOWED_HOSTS

class NotificationManager:
    def __init__(self):
        self.queues: Dict[str, List[asyncio.Queue]] = {}

    def get_queue(self, request_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if request_id not in self.queues:
            self.queues[request_id] = []
        self.queues[request_id].append(queue)
        return queue

    async def broadcast(self, request_id: str, message: Any):
        if request_id in self.queues:
            for queue in self.queues[request_id]:
                await queue.put(message)

    def remove_queues(self, request_id: str):
        if request_id in self.queues:
            del self.queues[request_id]

notifications = NotificationManager()


@app.on_event("startup")
async def clear_orphaned_workspaces():
    try:
        await asyncio.to_thread(drop_orphaned_collections)
    except Exception as e:
        logger.warning(f"Could not clear old workspace collections: {e}")

class GenerationRequest(BaseModel):
    request: str = Field(min_length=3, max_length=1000)
    word_count: Optional[int] = Field(default=800, ge=50, le=2000)
    tone: Optional[str] = Field(default="professional", max_length=30)
    webhook_url: Optional[HttpUrl] = None
    require_approval: Optional[bool] = False
    languages: Optional[List[str]] = Field(default_factory=list, max_length=3)
    generate_image: Optional[bool] = True
    generate_social_posts: Optional[bool] = True
    source: Literal["builtin", "documents", "web"] = "builtin"
    workspace_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")

async def send_webhook(url: str, payload: dict):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
            logger.info(f"Webhook sent to {url}")
    except Exception as e:
        logger.error(f"Failed to send webhook to {url}: {str(e)}")

async def run_pipeline(request_id: str, content_request: str, settings: dict, webhook_url: Optional[str] = None, require_approval: bool = False):
    jobs[request_id]["status"] = "processing"
    try:
        state = initialize_state(content_request, settings)
        state["request_id"] = request_id
        config = {"configurable": {"thread_id": request_id}}
        
        await asyncio.sleep(0.5)  # Give SSE client time to connect
        await notifications.broadcast(request_id, {"event": "started", "node": "planner"})
        
        # Pick the right workflow depending on whether HITL is requested
        active_workflow = workflow_app_hitl if require_approval else workflow_app
        logger.info(f"[{request_id[:8]}] Running {'with' if require_approval else 'without'} HITL")
        
        final_state = None
        async for event in active_workflow.astream(state, config=config):
            for node_name, node_output in event.items():
                logger.info(f"[{request_id[:8]}] Node '{node_name}' completed")
                await notifications.broadcast(request_id, {
                    "event": "node_complete", 
                    "node": node_name,
                    "status": "processing",
                    **({"summary": summarize_node(node_name, node_output)} if node_name in AGENT_ORDER else {}),
                })

        # Always use get_state() for the full accumulated pipeline state
        snapshot = active_workflow.get_state(config)
        
        # HITL path: check if pipeline paused for approval
        if require_approval and snapshot.next:
            jobs[request_id]["status"] = "awaiting_approval"
            jobs[request_id]["result"] = snapshot.values
            logger.info(f"[{request_id[:8]}] Pipeline paused — awaiting approval. Brief ready.")
            await notifications.broadcast(request_id, {
                "event": "awaiting_approval", 
                "brief": snapshot.values.get("brief")
            })
            return

        # Completed (HITL or non-HITL)
        final_state = snapshot.values
        if not final_state.get("final_content"):
            raise RuntimeError("; ".join(final_state.get("errors") or []) or "Pipeline finished without content")
            
        jobs[request_id]["status"] = "completed"
        jobs[request_id]["result"] = final_state
        await notifications.broadcast(request_id, {"event": "completed"})
        
        if webhook_url:
            payload = {"request_id": request_id, "status": "completed", "content": final_state.get("final_content")}
            await send_webhook(str(webhook_url), payload)
            
    except Exception as e:
        logger.error(f"Pipeline failed for {request_id}: {str(e)}", exc_info=True)
        jobs[request_id]["status"] = "failed"
        jobs[request_id]["error"] = str(e)
        await notifications.broadcast(request_id, {"event": "failed", "error": str(e)})
        if webhook_url:
            payload = {"request_id": request_id, "status": "failed", "error": str(e)}
            await send_webhook(str(webhook_url), payload)

@app.post("/api/v1/generate")
async def generate_content(req: GenerationRequest, background_tasks: BackgroundTasks):
    if req.webhook_url and not webhook_allowed(req.webhook_url):
        raise HTTPException(status_code=400, detail="webhook_url host is not allowed")
    collection = "research"
    overview = []
    if req.source == "documents":
        if not req.workspace_id:
            raise HTTPException(status_code=400, detail="workspace_id is required when source is documents")
        docs = get_workspace(req.workspace_id)["docs"]
        if not docs:
            raise HTTPException(status_code=400, detail="Upload at least one document first")
        collection = workspace_collection(req.workspace_id)
        overview = [{"name": d["name"], "preview": d.get("preview", "")} for d in docs.values()]
    if req.source == "web" and not Config.TAVILY_API_KEY:
        raise HTTPException(status_code=400, detail="Web search isn't set up on this server")
    request_id = str(uuid.uuid4())
    settings = {
        "word_count": req.word_count,
        "tone": req.tone,
        "languages": [lang.strip()[:30] for lang in req.languages or [] if lang.strip()],
        "generate_image": req.generate_image,
        "generate_social_posts": req.generate_social_posts,
        "source": req.source,
        "collection": collection,
        "source_overview": overview,
    }
    add_job(request_id, {"status": "pending", "request": req.request, "settings": settings, "result": None, "error": None})
    background_tasks.add_task(run_pipeline, request_id, req.request, settings, req.webhook_url, req.require_approval)
    return {"request_id": request_id, "status": "pending"}

@app.get("/api/v1/stream/{request_id}")
async def stream_status(request_id: str, just_replay: bool = False):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Unknown request ID")

    async def event_generator():
        # Yield a 'connected' event immediately so clients (and tests) see activity
        yield {"data": json.dumps({"event": "connected"}, default=str)}
        
        queue = notifications.get_queue(request_id)
        try:
            # Immediately replay current state for late-connecting clients
            current_job = jobs.get(request_id)
            if current_job:
                status = current_job.get("status")
                if status == "awaiting_approval":
                    brief = (current_job.get("result") or {}).get("brief")
                    yield {"data": json.dumps({"event": "awaiting_approval", "brief": brief}, default=str)}
                elif status == "completed":
                    yield {"data": json.dumps({"event": "completed"}, default=str)}
                    return
                elif status == "failed":
                    yield {"data": json.dumps({"event": "failed", "error": current_job.get("error")}, default=str)}
                    return
            
            if just_replay:
                return

            while True:
                message = await asyncio.wait_for(queue.get(), timeout=120.0)
                yield {"data": json.dumps(message, default=str)}
                if message.get("event") in ["completed", "failed"]:
                    break
        except asyncio.TimeoutError:
            yield {"data": json.dumps({"event": "failed", "error": "Stream timed out"}, default=str)}
        finally:
            notifications.remove_queues(request_id)
    return EventSourceResponse(event_generator())

@app.post("/api/v1/approve/{request_id}")
async def approve_content(request_id: str, background_tasks: BackgroundTasks):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
    if jobs[request_id]["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Job is not in awaiting_approval state")
    
    jobs[request_id]["status"] = "processing"
    async def resume_pipeline():
        try:
            config = {"configurable": {"thread_id": request_id}}
            await notifications.broadcast(request_id, {"event": "resuming", "node": "researcher"})
            # Always use the HITL workflow for resumption (it has the checkpointed state)
            async for event in workflow_app_hitl.astream(None, config=config):
                for node_name, node_output in event.items():
                    logger.info(f"[{request_id[:8]}] Resume: Node '{node_name}' completed")
                    await notifications.broadcast(request_id, {
                        "event": "node_complete",
                        "node": node_name,
                        "status": "processing",
                        **({"summary": summarize_node(node_name, node_output)} if node_name in AGENT_ORDER else {}),
                    })
            snapshot = workflow_app_hitl.get_state(config)
            if not snapshot.values.get("final_content"):
                raise RuntimeError("; ".join(snapshot.values.get("errors") or []) or "Pipeline finished without content")
            jobs[request_id]["status"] = "completed"
            jobs[request_id]["result"] = snapshot.values
            await notifications.broadcast(request_id, {"event": "completed"})
        except Exception as e:
            logger.error(f"Resume failed for {request_id}: {str(e)}", exc_info=True)
            jobs[request_id]["status"] = "failed"
            jobs[request_id]["error"] = str(e)
            await notifications.broadcast(request_id, {"event": "failed", "error": str(e)})
            
    background_tasks.add_task(resume_pipeline)
    return {"message": "Approval received, resuming pipeline."}

@app.get("/api/v1/status/{request_id}")
async def get_status(request_id: str):
    sweep_jobs()
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
    job = jobs[request_id]
    resp = {"request_id": request_id, "status": job["status"], "error": job["error"]}
    if job["status"] == "awaiting_approval" and job.get("result"):
        resp["brief"] = job["result"].get("brief")
    return resp

@app.get("/api/v1/config")
async def get_config():
    """Which optional features this server has turned on."""
    return {"web_search": bool(Config.TAVILY_API_KEY)}


def source_kind(settings: dict) -> str:
    if settings.get("source"):
        return settings["source"]
    return "documents" if settings.get("collection", "research") != "research" else "builtin"


@app.get("/api/v1/content/{request_id}")
async def get_content(request_id: str):
    sweep_jobs()
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
    job = jobs[request_id]
    if job["status"] not in ["completed", "awaiting_approval"]:
        return {"request_id": request_id, "status": job["status"], "message": "Content not ready."}
    result = job["result"]
    sources = {}
    for doc in result.get("retrieved_documents") or []:
        meta = doc.get("metadata") or {}
        url = meta.get("source") or doc.get("source")
        if url and url not in sources:
            sources[url] = {"title": meta.get("title") or url, "url": url}
    source_list = result.get("sources") or list(sources.values())
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", result.get("final_content") or "")}
    if cited & {s.get("n") for s in source_list}:
        source_list = [s for s in source_list if s.get("n") in cited]
    return {
        "request_id": request_id,
        "final_content": result.get("final_content"),
        "seo_metadata": result.get("seo_metadata"),
        "brief": result.get("brief"),
        "translated_content": result.get("translated_content"),
        "social_media_posts": result.get("social_media_posts"),
        "social_media_posts_by_language": result.get("social_media_posts_by_language"),
        "generated_images": result.get("generated_images"),
        "sources": source_list,
        "source_kind": source_kind(job.get("settings") or {}),
        "execution_times": result.get("execution_times") or {},
        "edit_notes": result.get("edit_notes"),
        "agents": summarize_run(result),
        "totals": run_totals(result),
    }

if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "Welcome to Digital Scribe API. UI not found."}
