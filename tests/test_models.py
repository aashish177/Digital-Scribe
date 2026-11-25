import pytest
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda

from agents.base import BaseAgent, model_settings
from agents.editor import EditorAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.seo import SEOAgent
from agents.writer import WriterAgent
from api.summaries import estimate_cost, run_totals
from config import Config


def test_quality_agents_use_the_strong_model():
    for agent in (WriterAgent(), EditorAgent(), ResearchAgent()):
        assert agent.model == Config.STRONG_MODEL
    for agent in (PlannerAgent(), SEOAgent()):
        assert agent.model == Config.FAST_MODEL
    assert {name for name, tier in Config.AGENT_TIERS.items() if tier == "strong"} == {"Research", "Writer", "Editor"}


def test_per_agent_override(monkeypatch):
    monkeypatch.setenv("MODEL_EDITOR", "gpt-4o-mini")
    assert Config.model_for("Editor") == "gpt-4o-mini"
    assert Config.model_for("Writer") == Config.STRONG_MODEL


def test_unknown_agent_defaults_to_strong():
    assert Config.model_for("SomethingNew") == Config.STRONG_MODEL


@pytest.mark.parametrize("model,expected", [
    ("gpt-4o", {"temperature": 0.2}),
    ("gpt-4o-mini-2024-07-18", {"temperature": 0.2}),
    ("gpt-6.1-terra", {"reasoning_effort": "low"}),
])
def test_temperature_only_for_models_that_accept_it(model, expected):
    assert model_settings(model, "strong", 0.2) == expected


def test_fast_tier_effort():
    assert model_settings("gpt-6-luna", "fast", 0.7) == {"reasoning_effort": Config.FAST_REASONING_EFFORT}


@pytest.mark.parametrize("model,prices", [
    ("gpt-6-luna", (0.10, 0.50)),
    ("gpt-4o-mini-2024-07-18", (0.15, 0.60)),
    ("gpt-4o-2024-08-06", (2.50, 10.00)),
    ("unknown-model", None),
])
def test_price_lookup(model, prices):
    assert Config.price_for(model) == prices


def test_cost_is_priced_per_model():
    usage = {"input_tokens": 2_000_000, "output_tokens": 0, "model": "gpt-6-luna",
             "by_model": {"gpt-6-luna": {"input_tokens": 1_000_000, "output_tokens": 0},
                          "gpt-6.1-terra": {"input_tokens": 1_000_000, "output_tokens": 0}}}
    assert estimate_cost(usage) == 1.10
    assert estimate_cost({"input_tokens": 10, "output_tokens": 10, "model": "unknown-model"}) is None


def test_run_totals_sum_each_agents_cost():
    state = {"execution_times": {"planner": 1.0, "writer": 2.0}, "usage": {
        "planner": {"input_tokens": 1_000_000, "output_tokens": 0, "model": "gpt-6-luna"},
        "writer": {"input_tokens": 0, "output_tokens": 1_000_000, "model": "gpt-6.1-terra"},
    }}
    totals = run_totals(state)
    assert totals["cost"] == 5.10
    assert totals["model"] == "gpt-6-luna + gpt-6.1-terra"


class Flaky(BaseAgent):
    """A fast agent whose output fails to parse unless it runs on the strong model."""

    def __init__(self):
        super().__init__(name="Planner")

        def run(_):
            if self.tier == "fast":
                raise OutputParserException("bad json")
            return {"ok": self.model}

        self.chain = RunnableLambda(run)


def test_fast_agent_retries_on_strong_model_when_output_is_invalid():
    agent = Flaky()
    assert agent.invoke({}) == {"ok": Config.STRONG_MODEL}
    assert agent.fallback_used is True
    assert agent.model == Config.FAST_MODEL


def test_strong_agent_does_not_retry():
    agent = Flaky()
    agent.tier = "strong"
    agent.chain = RunnableLambda(lambda _: (_ for _ in ()).throw(OutputParserException("bad json")))
    with pytest.raises(OutputParserException):
        agent.invoke({})


def test_other_errors_are_not_retried():
    agent = Flaky()
    agent.chain = RunnableLambda(lambda _: (_ for _ in ()).throw(RuntimeError("rate limited")))
    with pytest.raises(RuntimeError):
        agent.invoke({})
    assert agent.fallback_used is False
