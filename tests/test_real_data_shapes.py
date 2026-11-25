import json
from unittest.mock import MagicMock

import numpy as np
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from api.main import app, jobs
from vector_stores.chroma import ChromaDBManager


def test_stream_events_are_json():
    jobs["sse-json"] = {"status": "failed", "error": "boom", "result": None, "request": "r", "settings": {}}
    with TestClient(app).stream("GET", "/api/v1/stream/sse-json") as resp:
        events = [json.loads(line[len("data: "):]) for line in resp.iter_lines() if line.startswith("data: ")]
    jobs.pop("sse-json", None)
    assert events == [{"event": "connected"}, {"event": "failed", "error": "boom"}]


def test_rerank_scores_are_plain_floats(tmp_path, mocker):
    manager = ChromaDBManager(persistent_path=str(tmp_path))
    store = MagicMock()
    store.similarity_search.return_value = [Document(page_content="a"), Document(page_content="b")]
    mocker.patch.object(manager, "get_vector_store", return_value=store)
    mocker.patch.object(manager, "get_bm25_retriever", return_value=None)
    reranker = MagicMock()
    reranker.compress_documents.return_value = [
        Document(page_content="a", metadata={"relevance_score": np.float32(0.9)}),
        Document(page_content="b", metadata={"relevance_score": np.float32(0.4)}),
    ]
    mocker.patch.object(manager, "get_reranker", return_value=reranker)

    results = manager.query_multireturn("research", "q", k=2)

    assert [type(r["metadata"]["relevance_score"]) for r in results] == [float, float]
