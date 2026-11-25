import os

import pytest

# Agents build an OpenAI client on init; tests never call it, but it needs a key.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-used")

USAGE = {"input_tokens": 1000, "output_tokens": 200}


class FakeAgent:
    """Stands in for every agent so the real graph runs without model calls."""

    def __init__(self, *args, **kwargs):
        self.usage = dict(USAGE)

    def plan(self, request):
        return {"title": "T", "outline": ["a", "b"], "word_count_target": 50, "research_queries": ["q1", "q2"]}

    def research(self, queries):
        doc = {"content": "chunk", "metadata": {"title": "Heat pump", "source": "https://en.wikipedia.org/wiki/Heat_pump",
                                                "relevance_score": 0.9, "citation": 1}}
        return "findings [1]", [doc]

    def write(self, brief, research, sources=None):
        return "word " * 60

    def edit(self, draft, brief):
        return draft, "- tightened"

    def optimize(self, content, brief):
        return content, {"title": "SEO", "url_slug": "seo", "confidence": 0.9}

    def translate(self, content, lang):
        return f"[{lang}]"

    def generate_posts(self, content, brief):
        return {"linkedin": "post"}

    def generate_image_concept(self, title, summary):
        return {"prompt": "p", "style": "s"}

    def generate_image(self, prompt):
        return "https://placehold.co/1"


@pytest.fixture
def fake_agents(mocker):
    for name in ["PlannerAgent", "ResearchAgent", "WriterAgent", "EditorAgent", "SEOAgent",
                 "TranslatorAgent", "SocialMediaAgent", "ImageGenAgent"]:
        mocker.patch(f"graph.nodes.{name}", FakeAgent)
    return FakeAgent
