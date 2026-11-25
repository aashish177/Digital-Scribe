import pytest
from fastapi.testclient import TestClient

from api.main import app, jobs, add_job
from config import Config
from graph.workflow import create_content_workflow, initialize_state


def run(settings=None):
    graph = create_content_workflow(checkpointer="memory")
    config = {"configurable": {"thread_id": "safety"}}
    events = list(graph.stream(initialize_state("heat pumps", settings or {"word_count": 50}), config=config))
    return [node for e in events for node in e], graph.get_state(config).values


def test_writer_retries_are_capped(fake_agents, mocker):
    calls = mocker.patch.object(fake_agents, "write", return_value="too short")
    nodes, state = run()
    assert calls.call_count == Config.MAX_WRITER_ATTEMPTS
    assert "editor" in nodes


def test_writer_error_stops_after_cap(fake_agents, mocker):
    calls = mocker.patch.object(fake_agents, "write", side_effect=RuntimeError("rate limited"))
    nodes, state = run()
    assert calls.call_count == Config.MAX_WRITER_ATTEMPTS
    assert "editor" not in nodes
    assert state["errors"] == ["Writer error: rate limited"]


def test_planner_error_stops_pipeline(fake_agents, mocker):
    mocker.patch.object(fake_agents, "plan", side_effect=RuntimeError("bad json"))
    nodes, state = run()
    assert nodes == ["planner"]
    assert not state.get("final_content")


def test_sources_are_numbered_for_citations(fake_agents):
    _, state = run()
    assert state["sources"] == [{"n": 1, "title": "Heat pump", "url": "https://en.wikipedia.org/wiki/Heat_pump"}]


@pytest.fixture
def client():
    return TestClient(app)


def test_webhook_rejected_unless_allowlisted(client):
    resp = client.post("/api/v1/generate", json={"request": "AI ethics", "webhook_url": "https://169.254.169.254/latest"})
    assert resp.status_code == 400


@pytest.mark.parametrize("body", [
    {"request": "AI ethics", "word_count": 50000},
    {"request": "AI ethics", "languages": ["a", "b", "c", "d"]},
    {"request": "x" * 1001},
    {"request": "AI ethics", "tone": "t" * 31},
])
def test_oversized_requests_rejected(client, body):
    assert client.post("/api/v1/generate", json=body).status_code == 422


def test_job_store_is_capped(mocker):
    mocker.patch.object(Config, "MAX_JOBS_IN_MEMORY", 3)
    jobs.clear()
    for i in range(5):
        add_job(f"done-{i}", {"status": "completed"})
    add_job("running", {"status": "processing"})
    assert len(jobs) == 3
    assert "running" in jobs and "done-0" not in jobs
    jobs.clear()
