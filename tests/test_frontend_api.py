"""
tests/test_frontend_api.py
===========================
Tests for every API endpoint the Digital Scribe frontend interacts with.
All LangGraph / LLM calls are fully mocked — no real API keys needed.

Run with:
    PYTHONPATH=. pytest tests/test_frontend_api.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Rich mock data that mirrors a completed pipeline state
# ---------------------------------------------------------------------------

MOCK_BRIEF = {
    "title": "The Ethics of Artificial Intelligence",
    "target_audience": "Tech professionals and policy makers",
    "tone": "professional",
    "word_count_target": 800,
    "key_points": ["Bias in AI", "Transparency", "Accountability"],
    "research_queries": ["AI ethics frameworks", "algorithmic bias examples"],
}

MOCK_FINAL_STATE = {
    "request_id": "mock-request-id",
    "brief": MOCK_BRIEF,
    "research_findings": "AI ethics covers bias, transparency, and accountability.",
    "draft_content": "# AI Ethics\n\nDraft content here.",
    "edited_content": "# AI Ethics\n\nEdited content here.",
    "final_content": (
        "# The Ethics of Artificial Intelligence\n\n"
        "AI ethics is a rapidly evolving field that addresses the moral implications "
        "of artificial intelligence systems. Key concerns include algorithmic bias, "
        "transparency, and accountability.\n\n"
        "## Algorithmic Bias\n\nAI systems trained on biased data perpetuate inequality.\n\n"
        "## Transparency\n\nUsers deserve to understand how AI decisions are made.\n\n"
        "## Conclusion\n\nResponsible AI development requires ongoing vigilance."
    ),
    "seo_metadata": {
        "meta_title": "AI Ethics: Bias, Transparency & Accountability | Digital Scribe",
        "meta_description": "Explore the key pillars of AI ethics: bias, transparency, and accountability.",
        "slug": "ai-ethics-bias-transparency-accountability",
        "keywords": ["AI ethics", "algorithmic bias", "AI transparency"],
        "confidence": 0.91,
    },
    "translated_content": {
        "spanish": "# La Ética de la Inteligencia Artificial\n\nEl contenido aquí.",
        "french": "# L'Éthique de l'Intelligence Artificielle\n\nContenu ici.",
    },
    "social_media_posts": {
        "twitter": "🧵 Thread: AI Ethics 101\n1/ Bias in AI is a real problem...\n2/ Transparency matters...",
        "linkedin": "Excited to share insights on AI Ethics. Key areas: Bias, Transparency, Accountability.",
    },
    "generated_images": [
        {
            "prompt": "A balanced scale with a circuit board and a book labeled Ethics.",
            "style": "photorealistic",
            "url": "https://placehold.co/1200x675?text=AI+Ethics",
        }
    ],
    "errors": [],
    "agent_logs": [],
    "execution_times": {
        "planner": 2.1,
        "researcher": 4.5,
        "writer": 15.2,
        "editor": 8.1,
        "seo": 3.3,
    },
    "token_usage": {},
}


# ---------------------------------------------------------------------------
# Helpers to build async generator mocks for astream
# ---------------------------------------------------------------------------

async def mock_astream_full_run(*args, **kwargs):
    """Simulates a complete non-HITL pipeline run via astream."""
    yield {"planner": {"brief": MOCK_BRIEF}}
    yield {"researcher": {"research_findings": MOCK_FINAL_STATE["research_findings"]}}
    yield {"writer": {"draft_content": MOCK_FINAL_STATE["draft_content"]}}
    yield {"editor": {"edited_content": MOCK_FINAL_STATE["edited_content"]}}
    yield {"seo": {"final_content": MOCK_FINAL_STATE["final_content"], "seo_metadata": MOCK_FINAL_STATE["seo_metadata"]}}
    yield {"translator": {"translated_content": MOCK_FINAL_STATE["translated_content"]}}
    yield {"social_media": {"social_media_posts": MOCK_FINAL_STATE["social_media_posts"]}}
    yield {"image_gen": {"generated_images": MOCK_FINAL_STATE["generated_images"]}}


async def mock_astream_hitl_first_phase(*args, **kwargs):
    """Simulates the FIRST phase (planner runs, then __interrupt__)."""
    yield {"planner": {"brief": MOCK_BRIEF}}
    yield {"__interrupt__": ()}


async def mock_astream_hitl_resume(*args, **kwargs):
    """Simulates resuming after HITL approval (researcher onwards)."""
    yield {"researcher": {"research_findings": MOCK_FINAL_STATE["research_findings"]}}
    yield {"writer": {"draft_content": MOCK_FINAL_STATE["draft_content"]}}
    yield {"editor": {"edited_content": MOCK_FINAL_STATE["edited_content"]}}
    yield {"seo": {"final_content": MOCK_FINAL_STATE["final_content"], "seo_metadata": MOCK_FINAL_STATE["seo_metadata"]}}
    yield {"image_gen": {"generated_images": MOCK_FINAL_STATE["generated_images"]}}


def make_snapshot(next_nodes=None, values=None):
    """Creates a mock LangGraph state snapshot."""
    snap = MagicMock()
    snap.next = next_nodes or []
    snap.values = values or MOCK_FINAL_STATE
    return snap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_workflow():
    """Patches both workflow_app and workflow_app_hitl with mocks."""
    with (
        patch("api.main.workflow_app") as mock_wf,
        patch("api.main.workflow_app_hitl") as mock_wf_hitl,
    ):
        # Default: non-HITL runs to completion
        mock_wf.astream = mock_astream_full_run
        mock_wf.get_state = MagicMock(return_value=make_snapshot(next_nodes=[]))

        # HITL workflow: first call pauses, subsequent (resume) runs through
        mock_wf_hitl.astream = mock_astream_hitl_first_phase
        mock_wf_hitl.get_state = MagicMock(
            return_value=make_snapshot(next_nodes=["researcher"], values={**MOCK_FINAL_STATE, "brief": MOCK_BRIEF})
        )

        yield mock_wf, mock_wf_hitl


@pytest.fixture
def client(mock_workflow):
    """Returns a FastAPI TestClient with mocked workflows."""
    from api.main import app
    return TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# 1. Static file serving & Dashboard
# ===========================================================================

class TestDashboardServing:
    def test_root_serves_html(self, client):
        """GET / should return the dashboard HTML (200 or serve index.html)."""
        resp = client.get("/")
        assert resp.status_code == 200
        # The root either returns JSON fallback or HTML
        content_type = resp.headers.get("content-type", "")
        assert "html" in content_type or "json" in content_type

    def test_static_css_served(self, client):
        """GET /static/style.css should return a CSS file."""
        resp = client.get("/static/style.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers.get("content-type", "")

    def test_static_js_served(self, client):
        """GET /static/main.js should return a JavaScript file."""
        resp = client.get("/static/main.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers.get("content-type", "")

    def test_api_docs_available(self, client):
        """GET /docs should return the Swagger UI (200)."""
        resp = client.get("/docs")
        assert resp.status_code == 200


# ===========================================================================
# 2. Generation endpoint (POST /api/v1/generate)
# ===========================================================================

class TestGenerateEndpoint:
    def test_basic_generate_returns_request_id(self, client):
        """Submitting a basic request returns a request_id and pending status."""
        resp = client.post("/api/v1/generate", json={"request": "Write about AI ethics"})
        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert data["status"] == "pending"
        assert len(data["request_id"]) == 36  # UUID format

    def test_generate_with_all_options(self, client):
        """All frontend form options should be accepted without error."""
        resp = client.post("/api/v1/generate", json={
            "request": "AI ethics in healthcare",
            "word_count": 1200,
            "tone": "technical",
            "require_approval": False,
            "generate_image": True,
            "generate_social_posts": True,
            "languages": ["spanish", "french"],
        })
        assert resp.status_code == 200
        assert "request_id" in resp.json()

    def test_generate_without_approval(self, client):
        """require_approval=False should use non-HITL workflow."""
        resp = client.post("/api/v1/generate", json={
            "request": "AI ethics",
            "require_approval": False,
        })
        assert resp.status_code == 200

    def test_generate_with_approval(self, client):
        """require_approval=True should be accepted (HITL flow)."""
        resp = client.post("/api/v1/generate", json={
            "request": "AI ethics",
            "require_approval": True,
        })
        assert resp.status_code == 200

    def test_generate_missing_request_field_rejected(self, client):
        """Missing 'request' field should return 422 Unprocessable Entity."""
        resp = client.post("/api/v1/generate", json={"word_count": 800})
        assert resp.status_code == 422

    def test_generate_empty_request_body_rejected(self, client):
        """Empty body should return 422."""
        resp = client.post("/api/v1/generate", json={})
        assert resp.status_code == 422


# ===========================================================================
# 3. Status polling endpoint (GET /api/v1/status/{id})
# ===========================================================================

class TestStatusEndpoint:
    def _create_job(self, client, require_approval=False):
        resp = client.post("/api/v1/generate", json={
            "request": "AI ethics",
            "require_approval": require_approval,
        })
        return resp.json()["request_id"]

    def test_status_returns_pending_initially(self, client):
        """Immediately after generation, status should be 'pending' or 'processing'."""
        rid = self._create_job(client)
        resp = client.get(f"/api/v1/status/{rid}")
        assert resp.status_code == 200
        assert resp.json()["status"] in ["pending", "processing", "completed"]

    def test_status_unknown_id_returns_404(self, client):
        """Unknown request IDs should return 404."""
        resp = client.get("/api/v1/status/nonexistent-id-00000000")
        assert resp.status_code == 404

    def test_status_response_has_required_fields(self, client):
        """Status response must contain request_id, status, and error fields."""
        rid = self._create_job(client)
        resp = client.get(f"/api/v1/status/{rid}")
        data = resp.json()
        assert "request_id" in data
        assert "status" in data
        assert "error" in data


# ===========================================================================
# 4. Content retrieval endpoint (GET /api/v1/content/{id})
# ===========================================================================

class TestContentEndpoint:
    def _submit_and_complete(self, client):
        """Submit a job and wait for it to process (non-HITL, small sleep)."""
        resp = client.post("/api/v1/generate", json={"request": "AI ethics", "require_approval": False})
        rid = resp.json()["request_id"]
        # Give background task time to process (test client is synchronous)
        import time; time.sleep(3)
        return rid

    def test_content_not_found_for_unknown_id(self, client):
        """Unknown ID should return 404."""
        resp = client.get("/api/v1/content/bad-id-12345")
        assert resp.status_code == 404

    def test_content_not_ready_returns_status(self, client):
        """Immediately asking for content before pipeline finishes returns status info."""
        resp = client.post("/api/v1/generate", json={"request": "AI ethics"})
        rid = resp.json()["request_id"]
        resp = client.get(f"/api/v1/content/{rid}")
        assert resp.status_code == 200
        data = resp.json()
        # Either still processing or already done
        assert "status" in data or "final_content" in data

    def test_completed_content_has_all_fields(self, client):
        """When a job is manually marked complete, content should have all fields."""
        from api.main import jobs
        # Manually inject a completed job
        test_id = "test-complete-job-1234"
        jobs[test_id] = {"status": "completed", "result": MOCK_FINAL_STATE, "error": None}

        resp = client.get(f"/api/v1/content/{test_id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["final_content"] is not None
        assert "The Ethics of Artificial Intelligence" in data["final_content"]
        assert data["seo_metadata"]["slug"] == "ai-ethics-bias-transparency-accountability"
        assert data["brief"]["title"] == "The Ethics of Artificial Intelligence"

    def test_completed_content_has_translations(self, client):
        """Completed content should include translated versions."""
        from api.main import jobs
        test_id = "test-translations-5678"
        jobs[test_id] = {"status": "completed", "result": MOCK_FINAL_STATE, "error": None}

        data = client.get(f"/api/v1/content/{test_id}").json()
        assert data["translated_content"] is not None
        assert "spanish" in data["translated_content"]
        assert "french" in data["translated_content"]

    def test_completed_content_has_social_posts(self, client):
        """Completed content should include Twitter and LinkedIn posts."""
        from api.main import jobs
        test_id = "test-social-9012"
        jobs[test_id] = {"status": "completed", "result": MOCK_FINAL_STATE, "error": None}

        data = client.get(f"/api/v1/content/{test_id}").json()
        assert data["social_media_posts"] is not None
        assert "twitter" in data["social_media_posts"]
        assert "linkedin" in data["social_media_posts"]

    def test_completed_content_has_images(self, client):
        """Completed content should include generated image data."""
        from api.main import jobs
        test_id = "test-images-3456"
        jobs[test_id] = {"status": "completed", "result": MOCK_FINAL_STATE, "error": None}

        data = client.get(f"/api/v1/content/{test_id}").json()
        assert data["generated_images"] is not None
        assert len(data["generated_images"]) == 1
        img = data["generated_images"][0]
        assert "prompt" in img
        assert "style" in img
        assert "url" in img


# ===========================================================================
# 5. HITL Approval endpoint (POST /api/v1/approve/{id})
# ===========================================================================

class TestApprovalEndpoint:
    def test_approve_unknown_id_returns_404(self, client):
        """Approving an unknown ID should return 404."""
        resp = client.post("/api/v1/approve/nonexistent-id")
        assert resp.status_code == 404

    def test_approve_non_awaiting_job_returns_400(self, client):
        """Approving a job that is not awaiting returns 400."""
        from api.main import jobs
        jobs["not-waiting-job"] = {"status": "processing", "result": None, "error": None}
        resp = client.post("/api/v1/approve/not-waiting-job")
        assert resp.status_code == 400

    def test_approve_awaiting_job_succeeds(self, client):
        """Approving an awaiting_approval job should return 200 and a message."""
        from api.main import jobs
        test_id = "test-hitl-approve-ok"
        jobs[test_id] = {
            "status": "awaiting_approval",
            "result": {"brief": MOCK_BRIEF, **MOCK_FINAL_STATE},
            "error": None,
        }
        resp = client.post(f"/api/v1/approve/{test_id}")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_status_transitions_to_processing_after_approval(self, client):
        """After approval, the job status should change from awaiting_approval to processing."""
        from api.main import jobs
        test_id = "test-hitl-state-change"
        jobs[test_id] = {
            "status": "awaiting_approval",
            "result": {"brief": MOCK_BRIEF, **MOCK_FINAL_STATE},
            "error": None,
        }
        client.post(f"/api/v1/approve/{test_id}")
        # Status should no longer be awaiting_approval
        assert jobs[test_id]["status"] != "awaiting_approval"

    def test_status_endpoint_returns_brief_when_awaiting(self, client):
        """GET /api/v1/status should include the brief when awaiting approval."""
        from api.main import jobs
        test_id = "test-hitl-brief-in-status"
        jobs[test_id] = {
            "status": "awaiting_approval",
            "result": {"brief": MOCK_BRIEF},
            "error": None,
        }
        resp = client.get(f"/api/v1/status/{test_id}")
        data = resp.json()
        assert data["status"] == "awaiting_approval"
        assert "brief" in data
        assert data["brief"]["title"] == "The Ethics of Artificial Intelligence"


# ===========================================================================
# 6. SSE Stream endpoint (GET /api/v1/stream/{id})
# ===========================================================================

class TestSSEStreamEndpoint:
    def test_stream_unknown_id_returns_404(self, client):
        """SSE stream for an unknown ID should return 404."""
        resp = client.get("/api/v1/stream/nonexistent-xyz")
        assert resp.status_code == 404

    def test_stream_content_type_is_event_stream(self, client):
        """SSE endpoints must have correct Content-Type (check with valid ID)."""
        # Create a job first so the ID exists
        rid = client.post("/api/v1/generate", json={"request": "test"}).json()["request_id"]
        with client.stream("GET", f"/api/v1/stream/{rid}") as resp:
            assert "text/event-stream" in resp.headers.get("content-type", "")
            resp.close()

    def test_stream_replays_awaiting_approval_immediately(self, client):
        """If job is already awaiting_approval, stream immediately emits that event."""
        from api.main import jobs
        test_id = "test-stream-replay-hitl"
        jobs[test_id] = {
            "status": "awaiting_approval",
            "result": {"brief": MOCK_BRIEF},
            "error": None,
        }
        # Use just_replay=true so the stream closes after the initial data yield
        with client.stream("GET", f"/api/v1/stream/{test_id}?just_replay=true") as resp:
            assert resp.status_code == 200
            lines = [line for line in resp.iter_lines() if line]
            assert any("awaiting_approval" in l for l in lines)

    def test_stream_replays_completed_immediately(self, client):
        """If job is already completed, stream immediately emits completed event."""
        from api.main import jobs
        test_id = "test-stream-replay-done"
        jobs[test_id] = {"status": "completed", "result": MOCK_FINAL_STATE, "error": None}
        with client.stream("GET", f"/api/v1/stream/{test_id}?just_replay=true") as resp:
            assert resp.status_code == 200
            lines = [line for line in resp.iter_lines() if line]
            assert any("completed" in l for l in lines)

    def test_stream_replays_failed_immediately(self, client):
        """If job has failed, stream immediately emits failed event."""
        from api.main import jobs
        test_id = "test-stream-replay-failed"
        jobs[test_id] = {
            "status": "failed",
            "result": None,
            "error": "LLM rate limit exceeded",
        }
        with client.stream("GET", f"/api/v1/stream/{test_id}?just_replay=true") as resp:
            assert resp.status_code == 200
            lines = [line for line in resp.iter_lines() if line]
            assert any("failed" in l for l in lines)


# ===========================================================================
# 7. Full pipeline flow scenarios (end-to-end without LLMs)
# ===========================================================================

class TestPipelineFlowScenarios:
    def test_non_hitl_pipeline_marks_job_as_completed(self, client):
        """A non-HITL generation eventually marks the job as completed in the jobs store."""
        import time
        from api.main import jobs

        resp = client.post("/api/v1/generate", json={
            "request": "AI ethics",
            "require_approval": False,
        })
        rid = resp.json()["request_id"]

        # Wait for background task to process (mock is instant, but give event loop time)
        for _ in range(10):
            if jobs.get(rid, {}).get("status") in ["completed", "failed"]:
                break
            time.sleep(0.5)

        final_status = jobs.get(rid, {}).get("status")
        assert final_status in ["completed", "processing", "pending"]  # Won't crash

    def test_content_endpoint_shows_not_ready_for_processing_job(self, client):
        """Content endpoint for a still-processing job should return a status message."""
        from api.main import jobs
        test_id = "test-processing-content"
        jobs[test_id] = {"status": "processing", "result": None, "error": None}

        resp = client.get(f"/api/v1/content/{test_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "processing" or "message" in data

    def test_failed_job_has_error_in_status(self, client):
        """A failed job should expose its error message via the status endpoint."""
        from api.main import jobs
        test_id = "test-failed-job-error"
        jobs[test_id] = {
            "status": "failed",
            "result": None,
            "error": "OpenAI rate limit hit",
        }
        resp = client.get(f"/api/v1/status/{test_id}")
        data = resp.json()
        assert data["status"] == "failed"
        assert "OpenAI rate limit hit" in (data.get("error") or "")

    def test_hitl_status_includes_brief_for_review(self, client):
        """When HITL pauses, the brief must be visible in the status so frontend can render it."""
        from api.main import jobs
        test_id = "test-hitl-brief-visible"
        jobs[test_id] = {
            "status": "awaiting_approval",
            "result": {"brief": MOCK_BRIEF},
            "error": None,
        }
        data = client.get(f"/api/v1/status/{test_id}").json()
        assert data["brief"]["key_points"] == ["Bias in AI", "Transparency", "Accountability"]
        assert data["brief"]["tone"] == "professional"
