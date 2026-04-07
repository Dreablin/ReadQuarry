from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_settings_api_get_returns_defaults() -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_mode"] in {"ollama", "cloud"}
    assert "embedding_model" in payload


def test_settings_api_update_and_get_persists() -> None:
    response = client.put(
        "/api/settings",
        json={
            "llm_mode": "cloud",
            "provider": "openai",
            "api_key": "test-key",
            "model_id": "gpt-4o",
            "temperature": 0.3,
        },
    )
    assert response.status_code == 200

    after = client.get("/api/settings")
    assert after.status_code == 200
    payload = after.json()
    assert payload["llm_mode"] == "cloud"
    assert payload["provider"] == "openai"
    assert payload["api_key"] == "test-key"


def test_settings_api_rejects_cloud_without_api_key() -> None:
    response = client.put(
        "/api/settings",
        json={"llm_mode": "cloud", "provider": "openai", "api_key": ""},
    )
    assert response.status_code == 422


def test_settings_api_reset_restores_defaults() -> None:
    client.put("/api/settings", json={"llm_mode": "ollama", "ollama_base_url": "http://localhost:11434"})
    reset = client.post("/api/settings/reset")
    assert reset.status_code == 200
    defaults = client.get("/api/settings").json()
    assert defaults["llm_mode"] in {"ollama", "cloud"}


def test_settings_api_test_llm_endpoint() -> None:
    response = client.post("/api/settings/test-llm")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "error"}


def test_settings_api_rejects_invalid_llm_mode() -> None:
    response = client.put("/api/settings", json={"llm_mode": "invalid"})
    assert response.status_code == 422


def test_settings_api_rejects_temperature_out_of_range() -> None:
    response = client.put("/api/settings", json={"temperature": 3.0})
    assert response.status_code == 422


def test_settings_api_rejects_invalid_embedding_device() -> None:
    response = client.put("/api/settings", json={"embedding_device": "tpu"})
    assert response.status_code == 422


def test_settings_api_partial_update_preserves_other_fields() -> None:
    client.put(
        "/api/settings",
        json={
            "llm_mode": "cloud",
            "provider": "openai",
            "api_key": "k",
            "semantic_top_k": 9,
        },
    )
    response = client.put("/api/settings", json={"exact_results": 4})
    assert response.status_code == 200
    payload = response.json()
    assert payload["semantic_top_k"] == 9
    assert payload["exact_results"] == 4


def test_settings_api_rejects_non_positive_semantic_top_k() -> None:
    response = client.put("/api/settings", json={"semantic_top_k": 0})
    assert response.status_code == 422


def test_settings_api_rejects_malformed_ollama_url() -> None:
    response = client.put("/api/settings", json={"ollama_base_url": "not-a-url"})
    assert response.status_code == 422
