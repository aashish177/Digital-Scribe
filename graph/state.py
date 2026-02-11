from typing import TypedDict, List, Dict, Optional, Annotated
from operator import add

class ContentState(TypedDict):
    """
    Shared state for the content generation pipeline.
    """
    # Input
    content_request: str
    settings: Optional[Dict]
    
    # Planning Stage
    brief: Optional[Dict]  # JSON output from planner
    
    # Research Stage
    research_queries: Optional[List[str]]
    research_findings: Optional[str]
    retrieved_documents: Annotated[List[Dict], add]  # Accumulate docs
    
    # Writing Stage
    draft_content: Optional[str]
    
    # Editing Stage
    edited_content: Optional[str]
    edit_notes: Optional[str]
    
    # SEO Stage
    final_content: Optional[str]
    seo_metadata: Optional[Dict]
    
    # Error tracking and metadata
    errors: Annotated[List[str], add]
    agent_logs: Annotated[List[Dict], add]
    confidence_scores: Optional[Dict]
    
    # Execution tracking (Phase 2A)
    request_id: Optional[str]  # Unique ID for this pipeline run
    started_at: Optional[str]  # ISO timestamp when pipeline started
    execution_times: Optional[Dict[str, float]]  # Agent name -> execution time in seconds
    token_usage: Optional[Dict[str, int]]  # Agent name -> token count
