from langgraph.graph import END
from config import Config
from graph.state import ContentState

FAN_OUT = ["translator", "social_media", "image_gen"]


def check_errors(state: ContentState) -> str:
    """Stop the pipeline once a core step has failed."""
    return "error" if state.get("errors") else "continue"


def should_retry_writing(state: ContentState) -> str:
    """Retry a short or failed draft, up to MAX_WRITER_ATTEMPTS in total."""
    draft = state.get("draft_content") or ""
    attempts = state.get("writer_attempts") or 0
    brief = state.get("brief") or {}

    if state.get("errors"):
        return "error"

    if attempts >= Config.MAX_WRITER_ATTEMPTS:
        return "proceed" if draft else "error"

    if not draft:
        return "rewrite"

    target_words = brief.get("word_count_target", 800)
    if len(draft.split()) < target_words * 0.6:
        return "rewrite"

    return "proceed"


def after_seo(state: ContentState):
    """Fan out to the optional agents, or stop if SEO failed."""
    return END if state.get("errors") else FAN_OUT
