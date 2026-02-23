import pytest
from unittest.mock import MagicMock
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.writer import WriterAgent
from agents.editor import EditorAgent
from agents.seo import SEOAgent

@pytest.fixture
def mock_chain(mocker):
    # Mocking the base agent's get_chain method to return a mock chain
    mock = MagicMock()
    mocker.patch('agents.base.BaseAgent.get_chain', return_value=mock)
    return mock

def test_planner_agent(mock_chain):
    mock_chain.invoke.return_value = {
        "title": "A Test Title",
        "target_audience": "Developers",
        "tone": "Technical",
        "key_points": ["Point 1"],
        "word_count": 500,
        "formatting_requirements": ["Use Markdown"],
        "research_queries": ["query 1"]
    }
    
    agent = PlannerAgent()
    result = agent.plan("Write about a technical topic")
    
    assert mock_chain.invoke.called
    assert result["title"] == "A Test Title"
    assert "word_count" in result

def test_writer_agent(mock_chain):
    mock_chain.invoke.return_value = "This is the drafted content based on the brief."
    
    agent = WriterAgent()
    brief = {"title": "Test"}
    research_findings = "found some data"
    
    result = agent.write(brief, research_findings)
    
    assert mock_chain.invoke.called
    assert "drafted content" in result

def test_editor_agent(mock_chain):
    mock_chain.invoke.return_value = "This is the newly edited content.\n---DIVIDER---\nImproved clarity."
    
    agent = EditorAgent()
    draft = "This is drafted content."
    brief = {"title": "Test"}
    
    edited, notes = agent.edit(draft, brief)
    
    assert mock_chain.invoke.called
    assert "edited content" in edited
    assert "clarity" in notes

def test_seo_agent(mock_chain):
    mock_chain.invoke.return_value = {
        "optimized_content": "Optimized Content text.",
        "metadata": {
            "title": "SEO Title",
            "meta_description": "SEO Description",
            "keywords": ["a", "b"],
            "url_slug": "seo-slug",
            "confidence": 0.95
        }
    }
    
    agent = SEOAgent()
    content = "Original Content."
    brief = {"title": "Test Title"}
    
    final_content, metadata = agent.optimize(content, brief)
    
    assert mock_chain.invoke.called
    assert "Optimized Content" in final_content
    assert metadata["title"] == "SEO Title"
    assert metadata["confidence"] == 0.95

# Researcher Agent needs a different approach as it mocks vector stores as well
@pytest.fixture
def mock_chroma(mocker):
    mock_db = MagicMock()
    mocker.patch('vector_stores.chroma.ChromaDBManager', return_value=mock_db)
    return mock_db

def test_researcher_agent(mock_chain, mock_chroma):
    mock_chain.invoke.return_value = "Synthesized research findings."
    
    # Mock search functionality to return fake documents
    mock_doc = MagicMock()
    mock_doc.page_content = "Document content"
    mock_doc.metadata = {"source": "fake"}
    mock_chroma.search.return_value = [(mock_doc, 0.8)]
    
    agent = ResearchAgent()
    findings, docs = agent.research(["Test Query 1", "Test Query 2"])
    
    # Needs to be called for synthesis
    assert mock_chain.invoke.called
    assert "Synthesized" in findings
    assert len(docs) > 0 # Collected simulated docs
    assert "content" in docs[0]
