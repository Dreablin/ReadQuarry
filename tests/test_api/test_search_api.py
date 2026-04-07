from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


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
