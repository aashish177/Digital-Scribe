from langgraph.graph import StateGraph, END
from graph.state import ContentState
from graph.nodes import (
    planning_node,
    research_node,
    writing_node,
    editing_node,
    seo_node
)
from graph.edges import should_retry_writing, check_errors
from utils.logger import generate_request_id
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_content_workflow():
    """Creates the LangGraph workflow with error handling and logging."""
    
    logger.info("Creating content generation workflow")
    
    # Initialize graph
    workflow = StateGraph(ContentState)
    
    # Add nodes
    workflow.add_node("planner", planning_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("writer", writing_node)
    workflow.add_node("editor", editing_node)
    workflow.add_node("seo", seo_node)
    
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
    workflow.add_edge("seo", END)
    
    # Compile the graph
    app = workflow.compile()
    
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
        "errors": [],
        "agent_logs": [],
        "confidence_scores": None,
        # Execution tracking
        "request_id": request_id,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "execution_times": {},
        "token_usage": {}
    }
