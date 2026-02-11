from datetime import datetime
import logging
import time
from graph.state import ContentState
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.writer import WriterAgent
from agents.editor import EditorAgent
from agents.seo import SEOAgent
from errors import AgentError, PlannerError, ResearcherError, WriterError, EditorError, SEOError

logger = logging.getLogger(__name__)

def planning_node(state: ContentState) -> ContentState:
    """Planning agent node with error handling and logging."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    
    logger.info(f"[{request_id[:8]}] Planning node started")
    
    try:
        agent = PlannerAgent()
        request = state.get("content_request", "")
        brief = agent.plan(request)
        
        duration = time.time() - start_time
        
        # Update execution times
        execution_times = state.get("execution_times", {})
        execution_times["planner"] = duration
        
        logger.info(
            f"[{request_id[:8]}] Planning completed in {duration:.2f}s",
            extra={"extra_data": {"duration": duration, "request_id": request_id}}
        )
        
        return {
            "brief": brief,
            "research_queries": brief.get("research_queries", []),
            "execution_times": execution_times,
            "agent_logs": [{
                "agent": "planner",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "output": brief
            }]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id[:8]}] Planning failed after {duration:.2f}s: {str(e)}",
            extra={"extra_data": {"error": str(e), "duration": duration}},
            exc_info=True
        )
        return {
            "errors": [f"Planner error: {str(e)}"]
        }

def research_node(state: ContentState) -> ContentState:
    """Research agent node with error handling and logging."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    
    logger.info(f"[{request_id[:8]}] Research node started")
    
    try:
        agent = ResearchAgent()
        queries = state.get("research_queries", [])
        
        # Fallback if no queries
        if not queries:
            queries = [state["content_request"]]
            
        findings, docs = agent.research(queries)
        
        duration = time.time() - start_time
        execution_times = state.get("execution_times", {})
        execution_times["researcher"] = duration
        
        logger.info(
            f"[{request_id[:8]}] Research completed in {duration:.2f}s ({len(docs)} documents)",
            extra={"extra_data": {"duration": duration, "doc_count": len(docs)}}
        )
        
        return {
            "research_findings": findings,
            "retrieved_documents": docs,
            "execution_times": execution_times,
            "agent_logs": [{
                "agent": "research",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "document_count": len(docs)
            }]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id[:8]}] Research failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        return {
            "errors": [f"Research error: {str(e)}"]
        }

def writing_node(state: ContentState) -> ContentState:
    """Writing agent node with error handling and logging."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    
    logger.info(f"[{request_id[:8]}] Writing node started")
    
    try:
        agent = WriterAgent()
        draft = agent.write(
            brief=state.get("brief", {}),
            research=state.get("research_findings", "")
        )
        
        duration = time.time() - start_time
        execution_times = state.get("execution_times", {})
        execution_times["writer"] = duration
        word_count = len(draft.split())
        
        logger.info(
            f"[{request_id[:8]}] Writing completed in {duration:.2f}s ({word_count} words)",
            extra={"extra_data": {"duration": duration, "word_count": word_count}}
        )
        
        return {
            "draft_content": draft,
            "execution_times": execution_times,
            "agent_logs": [{
                "agent": "writer",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "word_count": word_count
            }]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id[:8]}] Writing failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        return {
            "errors": [f"Writer error: {str(e)}"]
        }

def editing_node(state: ContentState) -> ContentState:
    """Editing agent node with error handling and logging."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    
    logger.info(f"[{request_id[:8]}] Editing node started")
    
    try:
        agent = EditorAgent()
        edited, notes = agent.edit(
            draft=state.get("draft_content", ""),
            brief=state.get("brief", {})
        )
        
        duration = time.time() - start_time
        execution_times = state.get("execution_times", {})
        execution_times["editor"] = duration
        
        logger.info(
            f"[{request_id[:8]}] Editing completed in {duration:.2f}s",
            extra={"extra_data": {"duration": duration}}
        )
        
        return {
            "edited_content": edited,
            "edit_notes": notes,
            "execution_times": execution_times,
            "agent_logs": [{
                "agent": "editor",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "changes_made": notes
            }]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id[:8]}] Editing failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        return {
            "errors": [f"Editor error: {str(e)}"]
        }

def seo_node(state: ContentState) -> ContentState:
    """SEO agent node with error handling and logging."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    
    logger.info(f"[{request_id[:8]}] SEO node started")
    
    try:
        agent = SEOAgent()
        final, metadata = agent.optimize(
            content=state.get("edited_content", ""),
            brief=state.get("brief", {})
        )
        
        duration = time.time() - start_time
        execution_times = state.get("execution_times", {})
        execution_times["seo"] = duration
        
        logger.info(
            f"[{request_id[:8]}] SEO optimization completed in {duration:.2f}s",
            extra={"extra_data": {"duration": duration}}
        )
        
        return {
            "final_content": final,
            "seo_metadata": metadata,
            "execution_times": execution_times,
            "confidence_scores": {"seo": metadata.get("confidence", 0)},
            "agent_logs": [{
                "agent": "seo",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "metadata": metadata
            }]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id[:8]}] SEO optimization failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        return {
            "errors": [f"SEO error: {str(e)}"]
        }
