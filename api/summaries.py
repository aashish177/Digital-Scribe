from typing import Any, Dict, List, Optional

from config import Config

AGENT_ORDER = ["planner", "researcher", "writer", "editor", "seo", "translator", "social_media", "image_gen"]


def _cost(input_tokens: int, output_tokens: int, model: Optional[str]) -> Optional[float]:
    prices = Config.price_for(model) if model else None
    if not prices:
        return None
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000


def estimate_cost(usage: Optional[Dict[str, Any]]) -> Optional[float]:
    """Cost of one agent's usage, priced per model when it used more than one."""
    if not usage:
        return None
    parts = usage.get("by_model") or {usage.get("model") or Config.STRONG_MODEL: usage}
    costs = [_cost(u.get("input_tokens", 0), u.get("output_tokens", 0), m) for m, u in parts.items()]
    if any(c is None for c in costs):
        return None
    return round(sum(costs), 5)


def _chunks(docs: List[Dict], limit: int = 6) -> List[Dict]:
    chunks = []
    for doc in docs or []:
        meta = doc.get("metadata") or {}
        score = meta.get("relevance_score")
        chunks.append({
            "title": meta.get("title") or doc.get("source") or "Unknown",
            "url": meta.get("source") or doc.get("source"),
            "page": meta.get("page"),
            "citation": meta.get("citation"),
            "score": round(float(score), 3) if score is not None else None,
            "text": (doc.get("content") or "")[:240],
        })
    chunks.sort(key=lambda c: c["score"] if c["score"] is not None else -1, reverse=True)
    return chunks[:limit]


def summarize_node(node: str, output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Compact, UI-sized view of what one agent produced."""
    if not output:
        return {"skipped": True}

    summary: Dict[str, Any] = {}
    duration = (output.get("execution_times") or {}).get(node)
    usage = (output.get("usage") or {}).get(node)
    if duration is not None:
        summary["duration"] = round(duration, 2)
    if usage:
        summary["usage"] = usage
        summary["cost"] = estimate_cost(usage)
        if usage.get("model"):
            summary["model"] = usage["model"]
        if usage.get("fallback"):
            summary["fallback"] = True
    if output.get("errors"):
        summary["errors"] = output["errors"]

    if node == "planner":
        brief = output.get("brief") or {}
        summary.update({
            "title": brief.get("title"),
            "outline": brief.get("outline") or [],
            "queries": brief.get("research_queries") or [],
        })
    elif node == "researcher":
        docs = output.get("retrieved_documents") or []
        summary.update({
            "chunk_count": len(docs),
            "source_count": len({(d.get("metadata") or {}).get("source") for d in docs}),
            "chunks": _chunks(docs),
        })
    elif node == "writer":
        summary["word_count"] = len((output.get("draft_content") or "").split())
    elif node == "editor":
        summary["notes"] = output.get("edit_notes")
    elif node == "seo":
        meta = output.get("seo_metadata") or {}
        summary.update({"title": meta.get("title"), "slug": meta.get("url_slug")})
    elif node == "translator":
        summary["languages"] = list((output.get("translated_content") or {}).keys())
    elif node == "social_media":
        summary["platforms"] = list((output.get("social_media_posts") or {}).keys())
        summary["languages"] = list((output.get("social_media_posts_by_language") or {}).keys())
    elif node == "image_gen":
        images = output.get("generated_images") or []
        summary["prompt"] = images[0].get("prompt") if images else None
    return summary


def summarize_run(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Per-agent summaries rebuilt from the final pipeline state."""
    times = state.get("execution_times") or {}
    usage = state.get("usage") or {}
    agents = {}
    for node in AGENT_ORDER:
        if node not in times:
            agents[node] = {"skipped": True}
            continue
        output = dict(state)
        output["execution_times"] = {node: times[node]}
        output["usage"] = {node: usage[node]} if node in usage else {}
        output["errors"] = None
        agents[node] = summarize_node(node, output)
    writer_runs = sum(1 for log in state.get("agent_logs") or [] if log.get("agent") == "writer")
    if writer_runs > 1:
        agents["writer"]["attempts"] = writer_runs
    return agents


def run_totals(state: Dict[str, Any]) -> Dict[str, Any]:
    usage = state.get("usage") or {}
    total = {
        "input_tokens": sum(u.get("input_tokens", 0) for u in usage.values()),
        "output_tokens": sum(u.get("output_tokens", 0) for u in usage.values()),
    }
    costs = [estimate_cost(u) for u in usage.values()]
    models = sorted({u.get("model") for u in usage.values() if u.get("model")})
    return {
        "duration": round(sum((state.get("execution_times") or {}).values()), 2),
        "tokens": total["input_tokens"] + total["output_tokens"],
        "cost": round(sum(costs), 5) if costs and all(c is not None for c in costs) else None,
        "model": " + ".join(models) if models else None,
    }
