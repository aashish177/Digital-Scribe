import os
import time

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

import api.main as main
from config import Config
from graph.workflow import initialize_state
from vector_stores.chroma import ChromaDBManager, workspace_collection


def test_uploads_skip_the_embedding_cache(tmp_path, mocker):
    mocker.patch("vector_stores.chroma.OpenAIEmbeddings", return_value=DeterministicFakeEmbedding(size=16))
    manager = ChromaDBManager(persistent_path=str(tmp_path))
    cache_dir = tmp_path / "embeddings_cache"

    manager.add_documents("research", [Document(page_content="built-in chunk")])
    assert len(os.listdir(cache_dir)) == 1

    wid = "a" * 32
    manager.add_documents(workspace_collection(wid), [Document(page_content="private upload chunk")])
    assert len(os.listdir(cache_dir)) == 1
    assert manager.query(workspace_collection(wid), "upload", k=1)  # still searchable

    manager.drop_collection(workspace_collection(wid))
    assert workspace_collection(wid) not in manager.list_collections()


def run_job(fake_agents, request_id):
    config = {"configurable": {"thread_id": request_id}}
    state = initialize_state("heat pumps", {"word_count": 50})
    list(main.workflow_app.stream(state, config=config))
    main.add_job(request_id, {"status": "completed", "request": "r", "settings": {}, "error": None,
                              "result": main.workflow_app.get_state(config).values})
    return config


def test_forget_job_deletes_run_state(fake_agents):
    config = run_job(fake_agents, "forget-me")
    assert main.workflow_app.get_state(config).values.get("retrieved_documents")

    main.forget_job("forget-me")

    assert "forget-me" not in main.jobs
    assert main.workflow_app.get_state(config).values == {}


def test_old_runs_expire_but_running_ones_stay(fake_agents):
    config = run_job(fake_agents, "old-run")
    main.jobs["running"] = {"status": "processing", "created_at": time.time() - 10 * Config.JOB_TTL_SECONDS,
                            "result": None, "error": None, "settings": {}}
    try:
        main.sweep_jobs(now=time.time() + Config.JOB_TTL_SECONDS + 1)
        assert "old-run" not in main.jobs
        assert main.workflow_app.get_state(config).values == {}
        assert "running" in main.jobs
    finally:
        main.jobs.pop("running", None)


def test_recent_runs_are_kept(fake_agents):
    run_job(fake_agents, "recent-run")
    try:
        main.sweep_jobs()
        assert "recent-run" in main.jobs
    finally:
        main.forget_job("recent-run")


def test_job_cap_also_deletes_run_state(fake_agents, mocker):
    mocker.patch.object(Config, "MAX_JOBS_IN_MEMORY", 1)
    saved = dict(main.jobs)
    main.jobs.clear()
    try:
        first = run_job(fake_agents, "cap-1")
        run_job(fake_agents, "cap-2")
        assert "cap-1" not in main.jobs
        assert main.workflow_app.get_state(first).values == {}
    finally:
        main.forget_job("cap-2")
        main.jobs.update(saved)
