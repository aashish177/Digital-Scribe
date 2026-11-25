from datetime import datetime
import logging
import time
from graph.state import ContentState
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent, citation_label
from agents.writer import WriterAgent
from agents.editor import EditorAgent
from agents.seo import SEOAgent
from agents.translator import TranslatorAgent
from agents.social_media import SocialMediaAgent
from agents.image_gen import ImageGenAgent
from errors import AgentError, PlannerError, ResearcherError, WriterError, EditorError, SEOError
from config import Config

logger = logging.getLogger(__name__)


class NoRelevantSources(Exception):
    """Retrieval found nothing above the relevance cutoff."""


def _usage(execution_times: dict, agent) -> dict:
    name = next(iter(execution_times))
    usage = getattr(agent, "usage", None)
    if not isinstance(usage, dict):
        return {}
    usage = dict(usage)
    model = getattr(agent, "model", None)
    if isinstance(model, str):
        usage["model"] = model
        by_model = getattr(agent, "usage_by_model", None)
        if isinstance(by_model, dict) and by_model:
            usage["by_model"] = {m: dict(u) for m, u in by_model.items()}
        if getattr(agent, "fallback_used", False) is True:
            usage["fallback"] = True
    total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    return {"token_usage": {name: total}, "usage": {name: usage}}

def planning_node(state: ContentState) -> ContentState:
    """Planning agent node with error handling and logging."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    
    logger.info(f"[{request_id[:8]}] Planning node started")
    
    try:
        agent = PlannerAgent()
        request = state.get("content_request", "")
        brief = agent.plan(request, (state.get("settings") or {}).get("source_overview"))

        # Override brief with any user-supplied settings (word_count, tone)
        settings = state.get("settings") or {}
        if settings.get("word_count"):
            brief["word_count_target"] = settings["word_count"]
            logger.info(f"[{request_id[:8]}] Overriding word_count_target to {settings['word_count']}")
        if settings.get("tone"):
            brief["tone"] = settings["tone"]
            logger.info(f"[{request_id[:8]}] Overriding tone to {settings['tone']}")
        
        duration = time.time() - start_time
        
        # Update execution times
        execution_times = {}
        execution_times["planner"] = duration
        
        logger.info(
            f"[{request_id[:8]}] Planning completed in {duration:.2f}s",
            extra={"extra_data": {"duration": duration, "request_id": request_id}}
        )
        
        return {
            "brief": brief,
            "research_queries": brief.get("research_queries", []),
            "execution_times": execution_times,
            **_usage(execution_times, agent),
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
        queries = list(state.get("research_queries") or [])
        # The planner hasn't seen the documents and can misread names
        # (e.g. "Lumen" as the unit), so the user's own wording is always searched.
        request = (state.get("content_request") or "").strip()
        if request and request.lower() not in {q.lower() for q in queries}:
            queries.insert(0, request)
            
        settings = state.get("settings") or {}
        collection = settings.get("collection") or "research"
        findings, docs = agent.research(queries, collection=collection)
        if not docs:
            where = "your documents" if collection != "research" else "the built-in knowledge base"
            raise NoRelevantSources(f"No relevant passages in {where} for this topic. "
                                    "Try a topic the documents cover, or switch sources.")
        sources = {}
        for doc in docs:
            meta = doc.get("metadata") or {}
            n = meta.get("citation")
            if n is not None and n not in sources:
                url = meta.get("source") or doc.get("source")
                sources[n] = {"n": n, "title": citation_label(meta) if meta.get("title") else url or f"Source {n}",
                              "url": url, "page": meta.get("page")}
                if meta.get("doc_id"):
                    sources[n]["quote"] = " ".join((doc.get("content") or "").split())[:200]
        
        duration = time.time() - start_time
        execution_times = {}
        execution_times["researcher"] = duration
        
        logger.info(
            f"[{request_id[:8]}] Research completed in {duration:.2f}s ({len(docs)} documents)",
            extra={"extra_data": {"duration": duration, "doc_count": len(docs)}}
        )
        
        return {
            "research_findings": findings,
            "retrieved_documents": docs,
            "sources": [sources[n] for n in sorted(sources)],
            "execution_times": execution_times,
            **_usage(execution_times, agent),
            "agent_logs": [{
                "agent": "research",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "document_count": len(docs)
            }]
        }
        
    except NoRelevantSources as e:
        logger.info(f"[{request_id[:8]}] Research found nothing relevant")
        return {"errors": [str(e)], "execution_times": {"researcher": time.time() - start_time}}
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
    attempts = (state.get("writer_attempts") or 0) + 1
    
    try:
        agent = WriterAgent()
        draft = agent.write(
            brief=state.get("brief", {}),
            research=state.get("research_findings", ""),
            sources=state.get("sources") or [],
        )
        
        duration = time.time() - start_time
        execution_times = {}
        execution_times["writer"] = duration
        word_count = len(draft.split())
        
        logger.info(
            f"[{request_id[:8]}] Writing completed in {duration:.2f}s ({word_count} words)",
            extra={"extra_data": {"duration": duration, "word_count": word_count}}
        )
        
        result = {
            "draft_content": draft,
            "writer_attempts": attempts,
            "execution_times": execution_times,
            **_usage(execution_times, agent),
            "agent_logs": [{
                "agent": "writer",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "word_count": word_count
            }]
        }
        # A reply this short on the last attempt is a question or refusal, not an article.
        target = (state.get("brief") or {}).get("word_count_target", 800)
        if attempts >= Config.MAX_WRITER_ATTEMPTS and word_count < target * Config.MIN_DRAFT_RATIO:
            result["errors"] = [f"The writer returned only {word_count} words after {attempts} attempts. "
                                "Try a more specific topic."]
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id[:8]}] Writing failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        if attempts < Config.MAX_WRITER_ATTEMPTS:
            return {"draft_content": None, "writer_attempts": attempts}
        return {
            "errors": [f"Writer error: {str(e)}"],
            "writer_attempts": attempts,
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
            brief=state.get("brief", {}),
            findings=state.get("research_findings") or "",
        )
        
        duration = time.time() - start_time
        execution_times = {}
        execution_times["editor"] = duration
        
        logger.info(
            f"[{request_id[:8]}] Editing completed in {duration:.2f}s",
            extra={"extra_data": {"duration": duration}}
        )
        
        return {
            "edited_content": edited,
            "edit_notes": notes,
            "execution_times": execution_times,
            **_usage(execution_times, agent),
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
        execution_times = {}
        execution_times["seo"] = duration
        
        logger.info(
            f"[{request_id[:8]}] SEO optimization completed in {duration:.2f}s",
            extra={"extra_data": {"duration": duration}}
        )
        
        return {
            "final_content": final,
            "seo_metadata": metadata,
            "execution_times": execution_times,
            **_usage(execution_times, agent),
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

def translator_node(state: ContentState) -> ContentState:
    """Translator agent node."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    languages = state.get("target_languages", [])
    content = state.get("final_content", "")
    
    if not languages or not content:
        return {}
        
    logger.info(f"[{request_id[:8]}] Translator node started for languages: {languages}")
    
    try:
        agent = TranslatorAgent()
        translated = {}
        for lang in languages:
            translated[lang] = agent.translate(content, lang)
            
        duration = time.time() - start_time
        execution_times = {}
        execution_times["translator"] = duration
        
        return {
            "translated_content": translated,
            "execution_times": execution_times,
            **_usage(execution_times, agent),
            "agent_logs": [{
                "agent": "translator",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "languages": languages
            }]
        }
    except Exception as e:
        logger.error(f"[{request_id[:8]}] Translator failed: {str(e)}", exc_info=True)
        return {"errors": [f"Translator error: {str(e)}"]}

def social_media_node(state: ContentState) -> ContentState:
    """Social Media agent node."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    content = state.get("final_content", "")
    brief = state.get("brief", {})
    settings = state.get("settings") or {}
    
    if not content or not settings.get("generate_social_posts", True):
        return {}
        
    logger.info(f"[{request_id[:8]}] Social Media node started")
    # Posts follow the requested translation languages; English only when none were asked for.
    languages = state.get("target_languages") or ["English"]
    
    try:
        agent = SocialMediaAgent()
        by_language = {lang: agent.generate_posts(content, brief, lang) for lang in languages}
        posts = by_language[languages[0]]
        
        duration = time.time() - start_time
        execution_times = {}
        execution_times["social_media"] = duration
        
        return {
            "social_media_posts": posts,
            "social_media_posts_by_language": by_language,
            "execution_times": execution_times,
            **_usage(execution_times, agent),
            "agent_logs": [{
                "agent": "social_media",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "platforms": list(posts.keys()),
                "languages": languages,
            }]
        }
    except Exception as e:
        logger.error(f"[{request_id[:8]}] Social Media failed: {str(e)}", exc_info=True)
        return {"errors": [f"Social Media error: {str(e)}"]}

def image_gen_node(state: ContentState) -> ContentState:
    """Image Generation agent node."""
    start_time = time.time()
    request_id = state.get("request_id", "unknown")
    brief = state.get("brief", {})
    settings = state.get("settings") or {}
    
    if not settings.get("generate_image", True):
        return {}
        
    title = brief.get("title", "Article")
    
    logger.info(f"[{request_id[:8]}] Image Gen node started")
    
    try:
        agent = ImageGenAgent()
        # Create a concept summary
        summary = f"An article about {title}. Tone is {brief.get('tone', 'professional')}."
        concept = agent.generate_image_concept(title, summary)
        
        # Generate the image
        image_url = agent.generate_image(concept["prompt"])
        
        duration = time.time() - start_time
        execution_times = {}
        execution_times["image_gen"] = duration
        
        image_data = {
            "prompt": concept["prompt"],
            "style": concept["style"],
            "url": image_url
        }
        
        return {
            "generated_images": [image_data],
            "execution_times": execution_times,
            **_usage(execution_times, agent),
            "agent_logs": [{
                "agent": "image_gen",
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "image_data": image_data
            }]
        }
    except Exception as e:
        logger.error(f"[{request_id[:8]}] Image Gen failed: {str(e)}", exc_info=True)
        return {"errors": [f"Image Gen error: {str(e)}"]}
