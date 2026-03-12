from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
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
    title="Content Generation API",
    description="REST API for the Multi-Agent Content Creation Pipeline.",
    version="1.0.0"
)

# Setup initial configurations
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Compile the LangGraph pipeline once per worker
workflow_app = create_content_workflow(enable_hitl=True)

# In-memory store
jobs: Dict[str, Dict[str, Any]] = {}
batches: Dict[str, Dict[str, Any]] = {}

class GenerationRequest(BaseModel):
    request: str
    word_count: Optional[int] = 800
    tone: Optional[str] = "professional"
    webhook_url: Optional[HttpUrl] = None
    require_approval: Optional[bool] = False

class BatchGenerationRequest(BaseModel):
    requests: List[GenerationRequest]
    priority: Optional[str] = "normal"

async def send_webhook(url: str, payload: dict):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
            logger.info(f"Webhook sent successfully to {url}")
    except Exception as e:
        logger.error(f"Failed to send webhook to {url}: {str(e)}")

def run_pipeline(request_id: str, content_request: str, settings: dict, webhook_url: Optional[str] = None, require_approval: bool = False):
    jobs[request_id]["status"] = "processing"
    try:
        # initialize_state might generate its own UUID, but we overwrite it
        # with the request_id returned to the API caller to keep continuity.
        state = initialize_state(content_request, settings)
        state["request_id"] = request_id
        
        # Invoke the LangGraph synchronous workflow with thread tracing for HITL
        config = {"configurable": {"thread_id": request_id}}
        final_state = workflow_app.invoke(state, config=config)
        
        # Check if we hit the interrupt_before planner->researcher
        if require_approval:
            jobs[request_id]["status"] = "awaiting_approval"
            jobs[request_id]["result"] = workflow_app.get_state(config).values
            return
            
        # If no approval is required, automatically resume the pipeline from the interrupt point
        final_state = workflow_app.invoke(None, config=config)
        
        jobs[request_id]["status"] = "completed"
        jobs[request_id]["result"] = final_state
        
        if webhook_url:
            payload = {
                "request_id": request_id, 
                "status": "completed", 
                "content": final_state.get("final_content")
            }
            # Run webhook dispatch without blocking
            asyncio.create_task(send_webhook(str(webhook_url), payload))
            
    except Exception as e:
        logger.error(f"Pipeline failed for {request_id}: {str(e)}", exc_info=True)
        jobs[request_id]["status"] = "failed"
        jobs[request_id]["error"] = str(e)
        
        if webhook_url:
            payload = {
                "request_id": request_id, 
                "status": "failed", 
                "error": str(e)
            }
            asyncio.create_task(send_webhook(str(webhook_url), payload))


@app.post("/api/v1/generate")
async def generate_content(req: GenerationRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())
    
    settings = {
        "word_count": req.word_count,
        "tone": req.tone
    }
    
    jobs[request_id] = {
        "status": "pending",
        "request": req.request,
        "settings": settings,
        "result": None,
        "error": None
    }
    
    # Run pipeline asynchronously via background task
    background_tasks.add_task(
        run_pipeline, 
        request_id, 
        req.request, 
        settings, 
        webhook_url=str(req.webhook_url) if req.webhook_url else None,
        require_approval=req.require_approval
    )
    
    return {
        "request_id": request_id,
        "message": "Content generation started. Poll status endpoint for updates.",
        "status_url": f"/api/v1/status/{request_id}"
    }

@app.post("/api/v1/approve/{request_id}")
async def approve_content(request_id: str, background_tasks: BackgroundTasks):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
        
    if jobs[request_id]["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Request is not awaiting approval")
        
    jobs[request_id]["status"] = "processing"
    
    # Background task to resume from the interrupt
    def resume_pipeline():
        try:
            config = {"configurable": {"thread_id": request_id}}
            final_state = workflow_app.invoke(None, config=config)
            
            jobs[request_id]["status"] = "completed"
            jobs[request_id]["result"] = final_state
        except Exception as e:
            logger.error(f"Pipeline failed during resume for {request_id}: {str(e)}", exc_info=True)
            jobs[request_id]["status"] = "failed"
            jobs[request_id]["error"] = str(e)
            
    background_tasks.add_task(resume_pipeline)
    
    return {"message": "Pipeline approval received. Resuming generation."}


@app.post("/api/v1/batch")
async def batch_generate(req: BatchGenerationRequest, background_tasks: BackgroundTasks):
    batch_id = str(uuid.uuid4())
    request_ids = []
    
    for r in req.requests:
        request_id = str(uuid.uuid4())
        request_ids.append(request_id)
        
        settings = {"word_count": r.word_count, "tone": r.tone}
        jobs[request_id] = {
            "status": "pending",
            "request": r.request,
            "settings": settings,
            "result": None,
            "error": None,
            "batch_id": batch_id
        }
        
        background_tasks.add_task(
            run_pipeline, 
            request_id, 
            r.request, 
            settings, 
            webhook_url=str(r.webhook_url) if r.webhook_url else None,
            require_approval=r.require_approval
        )
        
    batches[batch_id] = {
        "batch_id": batch_id,
        "request_ids": request_ids,
        "status": "processing"
    }
    
    return {
        "batch_id": batch_id,
        "request_count": len(request_ids),
        "request_ids": request_ids,
        "status_url": f"/api/v1/batch/{batch_id}"
    }


@app.get("/api/v1/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    if batch_id not in batches:
        raise HTTPException(status_code=404, detail="Batch ID not found")
        
    batch = batches[batch_id]
    job_statuses = []
    completed_count = 0
    failed_count = 0
    
    for rid in batch["request_ids"]:
        if rid in jobs:
            status = jobs[rid]["status"]
            job_statuses.append({"request_id": rid, "status": status})
            if status == "completed":
                completed_count += 1
            if status == "failed":
                failed_count += 1
        else:
            job_statuses.append({"request_id": rid, "status": "unknown"})
            
    total = len(batch["request_ids"])
    batch_status = "processing"
    if completed_count + failed_count == total:
        batch_status = "completed"
    
    return {
        "batch_id": batch_id,
        "status": batch_status,
        "progress": f"{completed_count + failed_count}/{total}",
        "jobs": job_statuses
    }


@app.get("/api/v1/status/{request_id}")
async def get_status(request_id: str):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    resp = {"request_id": request_id, "status": jobs[request_id]["status"]}
    if jobs[request_id]["status"] == "failed":
        resp["error"] = jobs[request_id]["error"]
        
    # Expose the brief if it's awaiting approval
    if jobs[request_id]["status"] == "awaiting_approval" and jobs[request_id].get("result"):
        resp["brief"] = jobs[request_id]["result"].get("brief")
        
    return resp


@app.get("/api/v1/content/{request_id}")
async def get_content(request_id: str):
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Request ID not found")
        
    job = jobs[request_id]
    
    if job["status"] not in ["completed", "awaiting_approval"]:
        return {
            "request_id": request_id,
            "status": job["status"], 
            "message": "Content is not yet ready or processing failed."
        }
        
    result = job["result"]
    return {
        "request_id": request_id,
        "final_content": result.get("final_content"),
        "seo_metadata": result.get("seo_metadata"),
        "brief": result.get("brief")
    }
