from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from main import app
from src.api import search as search_module
from src.core.vector_store import VectorStore


client = TestClient(app)


@pytest.fixture
def isolated_search_data_dir(tmp_path: Path) -> Path:
    """Redirect search + chroma paths for API tests."""
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_search_api_b05_semantic_emits_time_tagged_duration(
    isolated_search_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B05: semantic search logs elapsed time with TIME tag (visible in /api/logs)."""
    monkeypatch.setattr(search_module, "settings", SimpleNamespace(data_dir=isolated_search_data_dir))
    query_vec = [0.02 * (i % 17) for i in range(384)]

    store = VectorStore(persist_directory=str(isolated_search_data_dir / "chroma"))
    store.add_documents(
        collection_name="book_77",
        ids=["77_0"],
        embeddings=[query_vec],
        documents=["b05 time tag doc"],
        metadatas=[{"book_id": 77, "chunk_index": 0}],
    )

    class _FixedEmbeddingService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def embed_text(self, text: str) -> list[float]:
            return query_vec

    monkeypatch.setattr(search_module, "EmbeddingService", _FixedEmbeddingService)
    monkeypatch.setattr(
        search_module,
        "get_settings",
        lambda: {
            "embedding_model": "dummy",
            "embedding_device": "cpu",
            "search_score_threshold": 0.0,
        },
    )

    tc = TestClient(app)
    r = tc.post("/api/search/semantic", json={"book_id": 77, "query": "q", "top_k": 3})
    assert r.status_code == 200
    body = tc.get("/api/logs").json()
    hits = [
        e
        for e in body["entries"]
        if e.get("tag") == "TIME" and "[TIME] Semantic search" in e.get("message", "") and "book_id=77" in e.get("message", "")
    ]
    assert hits, "expected TIME-tagged semantic search duration log"


def test_semantic_search_uses_chroma_not_placeholder(isolated_search_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """B02: semantic results must come from VectorStore, not hardcoded placeholder text."""
    monkeypatch.setattr(search_module, "settings", SimpleNamespace(data_dir=isolated_search_data_dir))
    query_vec = [0.02 * (i % 17) for i in range(384)]
    doc_vec = list(query_vec)  # identical vector -> strongest match with L2/cosine-style distance

    store = VectorStore(persist_directory=str(isolated_search_data_dir / "chroma"))
    store.add_documents(
        collection_name="book_42",
        ids=["42_0"],
        embeddings=[doc_vec],
        documents=["unique chroma document text xyz"],
        metadatas=[{"book_id": 42, "chunk_index": 0}],
    )

    class _FixedEmbeddingService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def embed_text(self, text: str) -> list[float]:
            return query_vec

    monkeypatch.setattr(search_module, "EmbeddingService", _FixedEmbeddingService)

    client = TestClient(app)
    response = client.post(
        "/api/search/semantic",
        json={"book_id": 42, "query": "any query", "top_k": 3},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "42_0"
    assert "unique chroma document text xyz" in results[0]["text"]
    assert "Semantic match for" not in results[0]["text"]


def test_semantic_search_returns_empty_when_no_collection_hits(isolated_search_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_module, "settings", SimpleNamespace(data_dir=isolated_search_data_dir))

    class _FixedEmbeddingService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def embed_text(self, text: str) -> list[float]:
            return [0.01] * 384

    monkeypatch.setattr(search_module, "EmbeddingService", _FixedEmbeddingService)
    client = TestClient(app)
    response = client.post(
        "/api/search/semantic",
        json={"book_id": 99, "query": "nothing", "top_k": 5},
    )
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_api_semantic_endpoint() -> None:
    response = client.post("/api/search/semantic", json={"book_id": 1, "query": "rabbit", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert isinstance(payload["results"], list)


def test_search_api_b05_exact_emits_time_tagged_duration(
    isolated_search_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B05: exact search logs elapsed time with TIME tag."""
    monkeypatch.setattr(search_module, "settings", SimpleNamespace(data_dir=isolated_search_data_dir))

    class _Eng:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def search(self, *a: object, **k: object) -> list:
            return []

    monkeypatch.setattr(search_module, "SearchEngine", _Eng)
    tc = TestClient(app)
    r = tc.post("/api/search/exact", json={"book_id": 55, "query": "needle", "max_results": 3})
    assert r.status_code == 200
    body = tc.get("/api/logs").json()
    hits = [
        e
        for e in body["entries"]
        if e.get("tag") == "TIME" and "[TIME] Exact search" in e.get("message", "") and "book_id=55" in e.get("message", "")
    ]
    assert hits


def test_search_api_exact_endpoint() -> None:
    response = client.post("/api/search/exact", json={"book_id": 1, "query": "rabbit", "max_results": 2})
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload


def test_search_api_b05_hybrid_emits_time_tagged_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    """B05: hybrid search logs total elapsed with TIME tag."""

    def _sem(_payload: object) -> dict:
        return {"results": []}

    def _ex(_payload: object) -> dict:
        return {"results": []}

    monkeypatch.setattr(search_module, "semantic_search", _sem)
    monkeypatch.setattr(search_module, "exact_search", _ex)
    monkeypatch.setattr(search_module, "get_settings", lambda: {"search_score_threshold": 0.0})

    tc = TestClient(app)
    r = tc.post(
        "/api/search/hybrid",
        json={"book_id": 88, "query": "hybridtime", "semantic_k": 2, "exact_k": 2, "final_n": 2},
    )
    assert r.status_code == 200
    body = tc.get("/api/logs").json()
    hits = [
        e
        for e in body["entries"]
        if e.get("tag") == "TIME" and "[TIME] Hybrid search" in e.get("message", "") and "book_id=88" in e.get("message", "")
    ]
    assert hits


def test_search_api_hybrid_endpoint() -> None:
    response = client.post(
        "/api/search/hybrid",
        json={"book_id": 1, "query": "rabbit", "semantic_k": 3, "exact_k": 3, "final_n": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert len(payload["results"]) <= 3


def test_search_api_rejects_empty_query() -> None:
    response = client.post("/api/search/semantic", json={"book_id": 1, "query": "", "top_k": 3})
    assert response.status_code == 422


def test_search_api_hybrid_respects_final_n() -> None:
    response = client.post(
        "/api/search/hybrid",
        json={"book_id": 1, "query": "rabbit", "semantic_k": 10, "exact_k": 10, "final_n": 1},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) <= 1


def test_search_api_rejects_non_positive_limits() -> None:
    response = client.post("/api/search/exact", json={"book_id": 1, "query": "rabbit", "max_results": 0})
    assert response.status_code == 422


def test_search_api_hybrid_rejects_final_n_over_50() -> None:
    """B05: cap hybrid limits so clients cannot request unbounded merges."""
    response = client.post(
        "/api/search/hybrid",
        json={"book_id": 1, "query": "rabbit", "semantic_k": 5, "exact_k": 5, "final_n": 51},
    )
    assert response.status_code == 422


def test_search_api_hybrid_accepts_final_n_50() -> None:
    """B05: allow up to 50 merged results."""
    response = client.post(
        "/api/search/hybrid",
        json={"book_id": 1, "query": "rabbit", "semantic_k": 50, "exact_k": 50, "final_n": 50},
    )
    assert response.status_code == 200
    assert "results" in response.json()


def test_semantic_search_applies_score_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """B04: semantic results below ``search_score_threshold`` are removed."""

    def _fake_chroma_to_results(raw: dict, top_k: int) -> list[dict]:
        return [
            {"chunk_id": "10", "text": "high", "score": 0.9},
            {"chunk_id": "11", "text": "low", "score": 0.35},
        ]

    monkeypatch.setattr(search_module, "_chroma_query_to_results", _fake_chroma_to_results)
    monkeypatch.setattr(
        search_module,
        "get_settings",
        lambda: {
            "embedding_model": "dummy",
            "embedding_device": "cpu",
            "search_score_threshold": 0.6,
        },
    )

    class _Emb:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def embed_text(self, text: str) -> list[float]:
            return [0.0] * 8

    monkeypatch.setattr(search_module, "EmbeddingService", _Emb)

    class _Store:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def query(self, *a: object, **k: object) -> dict:
            return {"ids": [[]], "documents": [[]], "distances": [[]]}

    monkeypatch.setattr(search_module, "VectorStore", _Store)

    r = client.post("/api/search/semantic", json={"book_id": 1, "query": "q", "top_k": 5})
    assert r.status_code == 200
    ids = [row["chunk_id"] for row in r.json()["results"]]
    assert ids == ["10"]


def test_semantic_search_all_below_threshold_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """B04: when every candidate is below threshold, return an empty list."""

    def _fake_chroma_to_results(raw: dict, top_k: int) -> list[dict]:
        return [{"chunk_id": "1", "text": "x", "score": 0.2}]

    monkeypatch.setattr(search_module, "_chroma_query_to_results", _fake_chroma_to_results)
    monkeypatch.setattr(
        search_module,
        "get_settings",
        lambda: {
            "embedding_model": "dummy",
            "embedding_device": "cpu",
            "search_score_threshold": 0.6,
        },
    )

    class _Emb:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def embed_text(self, text: str) -> list[float]:
            return [0.0] * 8

    monkeypatch.setattr(search_module, "EmbeddingService", _Emb)

    class _Store:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def query(self, *a: object, **k: object) -> dict:
            return {}

    monkeypatch.setattr(search_module, "VectorStore", _Store)

    r = client.post("/api/search/semantic", json={"book_id": 1, "query": "q", "top_k": 5})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_hybrid_search_applies_threshold_to_merged_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    """B04: hybrid filters merged rows by combined ``score``."""

    def _sem(_payload: object) -> dict:
        return {"results": [{"chunk_id": "1", "text": "a", "score": 0.95}]}

    def _ex(_payload: object) -> dict:
        return {"results": [{"chunk_id": "2", "text": "b", "score": 1.0}]}

    monkeypatch.setattr(search_module, "semantic_search", _sem)
    monkeypatch.setattr(search_module, "exact_search", _ex)
    monkeypatch.setattr(search_module, "get_settings", lambda: {"search_score_threshold": 1.5})

    r = client.post(
        "/api/search/hybrid",
        json={"book_id": 1, "query": "q", "semantic_k": 5, "exact_k": 5, "final_n": 10},
    )
    assert r.status_code == 200
    assert r.json()["results"] == []
