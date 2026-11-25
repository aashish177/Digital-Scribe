from api.summaries import estimate_cost, run_totals, summarize_node, summarize_run
from graph.workflow import create_content_workflow, initialize_state

USAGE = {"input_tokens": 1000, "output_tokens": 200}


def run(settings):
    app = create_content_workflow(checkpointer="memory")
    config = {"configurable": {"thread_id": "t"}}
    events = list(app.stream(initialize_state("heat pumps", settings), config=config))
    return events, app.get_state(config).values


def test_last_three_agents_run_in_one_parallel_step(fake_agents):
    events, state = run({"word_count": 50, "languages": ["spanish"]})
    assert set().union(*(e.keys() for e in events[-3:])) == {"translator", "social_media", "image_gen"}
    assert set(state["execution_times"]) == {"planner", "researcher", "writer", "editor", "seo",
                                             "translator", "social_media", "image_gen"}
    assert state["errors"] == []


def test_usage_is_recorded_per_agent(fake_agents):
    _, state = run({"word_count": 50})
    assert state["usage"]["writer"] == USAGE
    assert state["token_usage"]["writer"] == 1200


def test_planner_queries_reach_the_summary(fake_agents):
    _, state = run({"word_count": 50})
    agents = summarize_run(state)
    assert agents["planner"]["queries"] == ["q1", "q2"]
    assert agents["researcher"]["chunks"][0]["score"] == 0.9
    assert agents["translator"] == {"skipped": True}


def test_skipped_node_output_is_marked_skipped():
    assert summarize_node("social_media", None) == {"skipped": True}
    assert summarize_node("social_media", {}) == {"skipped": True}


def test_cost_uses_model_prices():
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 0, "model": "gpt-4o"}) == 2.5
    assert estimate_cost(None) is None


def test_run_totals_without_usage_has_no_cost():
    assert run_totals({"execution_times": {"planner": 1.0}})["cost"] is None
