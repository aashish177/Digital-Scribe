from datetime import datetime
from graph.state import ContentState
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent

# Placeholder Agent Classes (to be replaced with actual implementations)
# ResearchAgent is now real and imported above

class WriterAgent:
    def write(self, brief, research):
        return f"Draft content based on brief: {brief.get('topic', 'unknown')} and research."

class EditorAgent:
    def edit(self, draft, brief):
        return f"Edited: {draft}", "Fixed specific grammar issues."

class SEOAgent:
    def optimize(self, content, brief):
        return f"SEO Optimized: {content}", {"title": "SEO Title", "confidence": 0.9}

def planning_node(state: ContentState) -> ContentState:
    """Planning agent node"""
    try:
        try:
            agent = PlannerAgent()
            # Ensure we have a string for the request
            request = state.get("content_request", "")
            brief = agent.plan(request)
        except Exception as e:
            print(f"WARNING: PlannerAgent failed ({str(e)}). Using mock brief for testing.")
            brief = {
                "title": "Guide to Green Tea",
                "target_audience": "Health enthusiasts",
                "tone": "Informative",
                "word_count": 500,
                "research_queries": ["green tea health benefits", "green tea antioxidants", "caffeine in green tea"]
            }
        
        return {
            "brief": brief,
            "research_queries": brief.get("research_queries", []),
            "agent_logs": [{
                "agent": "planner",
                "timestamp": datetime.now().isoformat(),
                "output": brief
            }]
        }
    except Exception as e:
        return {
            "errors": [f"Planner error: {str(e)}"]
        }

def research_node(state: ContentState) -> ContentState:
    """Research agent node"""
    try:
        agent = ResearchAgent()
        queries = state.get("research_queries", [])
        
        # Fallback if no queries
        if not queries:
            queries = [state["content_request"]]
            
        findings, docs = agent.research(queries)
        
        return {
            "research_findings": findings,
            "retrieved_documents": docs,
            "agent_logs": [{
                "agent": "research",
                "timestamp": datetime.now().isoformat(),
                "document_count": len(docs)
            }]
        }
    except Exception as e:
        return {
            "errors": [f"Research error: {str(e)}"]
        }

def writing_node(state: ContentState) -> ContentState:
    """Writing agent node"""
    try:
        agent = WriterAgent()
        draft = agent.write(
            brief=state.get("brief", {}),
            research=state.get("research_findings", "")
        )
        
        return {
            "draft_content": draft,
            "agent_logs": [{
                "agent": "writer",
                "timestamp": datetime.now().isoformat(),
                "word_count": len(draft.split())
            }]
        }
    except Exception as e:
        return {
            "errors": [f"Writer error: {str(e)}"]
        }

def editing_node(state: ContentState) -> ContentState:
    """Editing agent node"""
    try:
        agent = EditorAgent()
        edited, notes = agent.edit(
            draft=state.get("draft_content", ""),
            brief=state.get("brief", {})
        )
        
        return {
            "edited_content": edited,
            "edit_notes": notes,
            "agent_logs": [{
                "agent": "editor",
                "timestamp": datetime.now().isoformat(),
                "changes_made": notes
            }]
        }
    except Exception as e:
        return {
            "errors": [f"Editor error: {str(e)}"]
        }

def seo_node(state: ContentState) -> ContentState:
    """SEO agent node"""
    try:
        agent = SEOAgent()
        final, metadata = agent.optimize(
            content=state.get("edited_content", ""),
            brief=state.get("brief", {})
        )
        
        return {
            "final_content": final,
            "seo_metadata": metadata,
            "confidence_scores": {"seo": metadata.get("confidence", 0)},
            "agent_logs": [{
                "agent": "seo",
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata
            }]
        }
    except Exception as e:
        return {
            "errors": [f"SEO error: {str(e)}"]
        }
