from graph.state import ContentState

def should_retry_writing(state: ContentState) -> str:
    """Check if draft needs rewriting due to insufficient word count."""
    draft = state.get("draft_content", "")
    brief = state.get("brief", {})
    
    # Simple check for empty draft
    if not draft:
        return "rewrite"
    
    # Use the correct field name: word_count_target
    target_words = brief.get("word_count_target", 800)
    actual_words = len(draft.split())
    
    # Retry if draft is less than 60% of the target word count
    if actual_words < target_words * 0.6:
        return "rewrite"
    
    return "proceed"

def should_retry_editing(state: ContentState) -> str:
    """Check editing quality"""
    confidence = state.get("confidence_scores", {}).get("editing", 1.0)
    
    if confidence < 0.7:
        return "re_edit"
    
    return "proceed"

def check_errors(state: ContentState) -> str:
    """Check for fatal errors"""
    if state.get("errors"):
        return "error"
    
    return "continue"
