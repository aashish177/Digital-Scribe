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
from graph.edges import FAN_OUT, after_seo, check_errors, should_retry_writing
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
    
    # Core steps stop the run on error; the last three fan out in parallel.
    workflow.add_conditional_edges("planner", check_errors, {"continue": "researcher", "error": END})
    workflow.add_conditional_edges("researcher", check_errors, {"continue": "writer", "error": END})
    workflow.add_conditional_edges(
        "writer",
        should_retry_writing,
        {"rewrite": "writer", "proceed": "editor", "error": END}
    )
    workflow.add_conditional_edges("editor", check_errors, {"continue": "seo", "error": END})
    workflow.add_conditional_edges("seo", after_seo, FAN_OUT + [END])
    for node in FAN_OUT:
        workflow.add_edge(node, END)
    
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
        "sources": [],
        "draft_content": None,
        "writer_attempts": 0,
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
        "token_usage": {},
        "usage": {}
    }
