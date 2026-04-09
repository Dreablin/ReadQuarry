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


def test_search_api_exact_endpoint() -> None:
    response = client.post("/api/search/exact", json={"book_id": 1, "query": "rabbit", "max_results": 2})
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload


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
