from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import ContentState
from graph.nodes import (
    planning_node,
    research_node,
    writing_node,
    editing_node,
    seo_node,
    translator_node,
    social_media_node,
    image_gen_node
)
from graph.edges import should_retry_writing, check_errors
from utils.logger import generate_request_id
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_content_workflow(enable_hitl: bool = False, checkpointer = None):
    """
    Creates the LangGraph workflow.
    
    Args:
        enable_hitl: If True, adds an interrupt before the researcher node to allow brief review.
        checkpointer: Custom checkpointer to use. If enable_hitl is True and none is provided, uses MemorySaver.
    """
    
    logger.info("Creating content generation workflow")
    
    # Initialize graph
    workflow = StateGraph(ContentState)
    
    # Add nodes
    workflow.add_node("planner", planning_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("writer", writing_node)
    workflow.add_node("editor", editing_node)
    workflow.add_node("seo", seo_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("social_media", social_media_node)
    workflow.add_node("image_gen", image_gen_node)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Add edges (linear flow with conditionals)
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    
    # Conditional edge: check if writing needs retry
    workflow.add_conditional_edges(
        "writer",
        should_retry_writing,
        {
            "rewrite": "writer",  # Loop back
            "proceed": "editor"
        }
    )
    
    # TODO: Add error handling edges using check_errors if needed
    
    workflow.add_edge("editor", "seo")
    workflow.add_edge("seo", "translator")
    workflow.add_edge("translator", "social_media")
    workflow.add_edge("social_media", "image_gen")
    workflow.add_edge("image_gen", END)
    
    # Setup Human-in-the-loop if enabled
    kwargs = {}
    if enable_hitl:
        kwargs["interrupt_before"] = ["researcher"]
        if checkpointer is None:
            checkpointer = MemorySaver()
    
    # Accept "memory" as a shorthand to create a MemorySaver
    if checkpointer == "memory":
        checkpointer = MemorySaver()
    
    # Always attach a checkpointer so get_state() works on any compiled app
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    if checkpointer:
        kwargs["checkpointer"] = checkpointer
        
    # Compile the graph
    app = workflow.compile(**kwargs)
    
    logger.info("Workflow created successfully")
    
    return app


def initialize_state(content_request: str, settings: dict = None) -> ContentState:
    """
    Initialize state with execution tracking metadata.
    
    Args:
        content_request: The content request from the user
        settings: Optional settings dictionary
    
    Returns:
        Initialized ContentState with tracking fields
    """
    request_id = generate_request_id()
    
    logger.info(
        f"Initializing pipeline state",
        extra={"extra_data": {"request_id": request_id}}
    )
    
    return {
        "content_request": content_request,
        "settings": settings,
        "brief": None,
        "research_queries": None,
        "research_findings": None,
        "retrieved_documents": [],
        "draft_content": None,
        "edited_content": None,
        "edit_notes": None,
        "final_content": None,
        "seo_metadata": None,
        # Phase 3C: New Modalities
        "target_languages": settings.get("languages", []) if settings else [],
        "translated_content": {},
        "social_media_posts": {},
        "generated_images": [],
        "errors": [],
        "agent_logs": [],
        "confidence_scores": None,
        # Execution tracking
        "request_id": request_id,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "execution_times": {},
        "token_usage": {}
    }
