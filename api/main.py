from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
from sse_starlette.sse import EventSourceResponse
from graph.workflow import create_content_workflow, initialize_state
import logging
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

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup initial configurations
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Compile TWO workflow variants once per worker, both with MemorySaver
# so get_state() works on either to retrieve the full accumulated pipeline state.
workflow_app = create_content_workflow(enable_hitl=False, checkpointer="memory")
workflow_app_hitl = create_content_workflow(enable_hitl=True)

# In-memory store
jobs: Dict[str, Dict[str, Any]] = {}
batches: Dict[str, Dict[str, Any]] = {}

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

class GenerationRequest(BaseModel):
    request: str
    word_count: Optional[int] = 800
    tone: Optional[str] = "professional"
    webhook_url: Optional[HttpUrl] = None
    require_approval: Optional[bool] = False
    languages: Optional[List[str]] = []
    generate_image: Optional[bool] = True
    generate_social_posts: Optional[bool] = True

class BatchGenerationRequest(BaseModel):
    requests: List[GenerationRequest]
    priority: Optional[str] = "normal"

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
                    "status": "processing"
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
    request_id = str(uuid.uuid4())
    settings = {
        "word_count": req.word_count,
        "tone": req.tone,
        "languages": req.languages,
        "generate_image": req.generate_image,
        "generate_social_posts": req.generate_social_posts
    }
    jobs[request_id] = {"status": "pending", "request": req.request, "settings": settings, "result": None, "error": None}
    background_tasks.add_task(run_pipeline, request_id, req.request, settings, req.webhook_url, req.require_approval)
    return {"request_id": request_id, "status": "pending"}

@app.get("/api/v1/stream/{request_id}")
async def stream_status(request_id: str, just_replay: bool = False):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Unknown request ID")

    async def event_generator():
        # Yield a 'connected' event immediately so clients (and tests) see activity
        yield {"data": {"event": "connected"}}
        
        queue = notifications.get_queue(request_id)
        try:
            # Immediately replay current state for late-connecting clients
            current_job = jobs.get(request_id)
            if current_job:
                status = current_job.get("status")
                if status == "awaiting_approval":
                    brief = (current_job.get("result") or {}).get("brief")
                    yield {"data": {"event": "awaiting_approval", "brief": brief}}
                elif status == "completed":
                    yield {"data": {"event": "completed"}}
                    return
                elif status == "failed":
                    yield {"data": {"event": "failed", "error": current_job.get("error")}}
                    return
            
            if just_replay:
                return

            while True:
                message = await asyncio.wait_for(queue.get(), timeout=120.0)
                yield {"data": message}
                if message.get("event") in ["completed", "failed"]:
                    break
        except asyncio.TimeoutError:
            yield {"data": {"event": "failed", "error": "Stream timed out"}}
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
                    await notifications.broadcast(request_id, {"event": "node_complete", "node": node_name, "status": "processing"})
            snapshot = workflow_app_hitl.get_state(config)
            jobs[request_id]["status"] = "completed"
            jobs[request_id]["result"] = snapshot.values
            await notifications.broadcast(request_id, {"event": "completed"})
        except Exception as e:
            logger.error(f"Resume failed for {request_id}: {str(e)}", exc_info=True)
            jobs[request_id]["status"] = "failed"
            await notifications.broadcast(request_id, {"event": "failed", "error": str(e)})
            
    background_tasks.add_task(resume_pipeline)
    return {"message": "Approval received, resuming pipeline."}

@app.get("/api/v1/status/{request_id}")
async def get_status(request_id: str):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
    job = jobs[request_id]
    resp = {"request_id": request_id, "status": job["status"], "error": job["error"]}
    if job["status"] == "awaiting_approval" and job.get("result"):
        resp["brief"] = job["result"].get("brief")
    return resp

@app.get("/api/v1/content/{request_id}")
async def get_content(request_id: str):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
    job = jobs[request_id]
    if job["status"] not in ["completed", "awaiting_approval"]:
        return {"request_id": request_id, "status": job["status"], "message": "Content not ready."}
    result = job["result"]
    return {
        "request_id": request_id,
        "final_content": result.get("final_content"),
        "seo_metadata": result.get("seo_metadata"),
        "brief": result.get("brief"),
        "translated_content": result.get("translated_content"),
        "social_media_posts": result.get("social_media_posts"),
        "generated_images": result.get("generated_images")
    }

if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "Welcome to Digital Scribe API. UI not found."}
