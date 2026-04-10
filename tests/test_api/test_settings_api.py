from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from main import app
from src.api import settings as settings_module


client = TestClient(app)


def test_settings_persist_to_disk_and_reload_simulates_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B03: values saved via API must be loadable from settings.json after a simulated process restart."""
    monkeypatch.setattr(
        settings_module,
        "app_config",
        SimpleNamespace(data_dir=tmp_path),
    )
    settings_module._SETTINGS.clear()
    settings_module._SETTINGS.update(dict(settings_module.DEFAULTS))

    c = TestClient(app)
    custom_url = "http://127.0.0.1:19999"
    r = c.put("/api/settings", json={"ollama_base_url": custom_url})
    assert r.status_code == 200

    path = tmp_path / "settings.json"
    assert path.is_file(), "settings should be written to data_dir/settings.json"

    settings_module._SETTINGS.clear()
    settings_module._SETTINGS.update(dict(settings_module.DEFAULTS))
    settings_module._merge_file_into_settings()

    after = c.get("/api/settings").json()
    assert after["ollama_base_url"] == custom_url


def test_settings_api_get_returns_defaults() -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_mode"] in {"ollama", "cloud"}
    assert "embedding_model" in payload


def test_settings_api_b03a_system_prompt_in_defaults() -> None:
    """B03a: system_prompt is in DEFAULTS and returned by GET."""
    assert "system_prompt" in settings_module.DEFAULTS
    sp = str(settings_module.DEFAULTS["system_prompt"])
    assert "ReadQuarry" in sp
    assert "[1]" in sp or "[2]" in sp
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["system_prompt"] == sp


def test_settings_api_b03a_system_prompt_update_via_put(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B03a: system_prompt can be updated with PUT and persists."""
    monkeypatch.setattr(settings_module, "app_config", SimpleNamespace(data_dir=tmp_path))
    settings_module._SETTINGS.clear()
    settings_module._SETTINGS.update(dict(settings_module.DEFAULTS))

    c = TestClient(app)
    custom = "You are a test assistant. Be brief."
    r = c.put("/api/settings", json={"system_prompt": custom})
    assert r.status_code == 200
    assert r.json()["system_prompt"] == custom
    assert c.get("/api/settings").json()["system_prompt"] == custom

    path = tmp_path / "settings.json"
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["system_prompt"] == custom


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


def test_settings_api_test_llm_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /test-llm returns 200 with status ok or error (never relies on real network)."""

    class _Ok:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def chat_completion(self, *a: object, **k: object) -> None:
            return None

    monkeypatch.setattr(settings_module, "LLMClient", _Ok)
    client.post("/api/settings/reset")
    response = client.post("/api/settings/test-llm")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "ollama"
    assert "model" in data


def test_settings_test_llm_returns_error_when_chat_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """B14: failed connectivity returns HTTP 200 with status error and detail (for frontend JSON)."""

    class _Fail:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def chat_completion(self, *a: object, **k: object) -> None:
            raise RuntimeError("connection refused (test)")

    monkeypatch.setattr(settings_module, "LLMClient", _Fail)
    client.post("/api/settings/reset")
    response = client.post("/api/settings/test-llm")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "connection refused" in data["detail"]


def test_settings_test_llm_cloud_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """B14: cloud mode without api_key cannot run a test."""
    client.post("/api/settings/reset")
    monkeypatch.setitem(settings_module._SETTINGS, "llm_mode", "cloud")
    monkeypatch.setitem(settings_module._SETTINGS, "api_key", "")
    response = client.post("/api/settings/test-llm")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "api_key" in data["detail"].lower()


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


def test_settings_api_search_score_threshold_default_and_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B03: search_score_threshold defaults to 0.6 and persists in settings.json."""
    monkeypatch.setattr(settings_module, "app_config", SimpleNamespace(data_dir=tmp_path))
    settings_module._SETTINGS.clear()
    settings_module._SETTINGS.update(dict(settings_module.DEFAULTS))

    c = TestClient(app)
    r = c.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["search_score_threshold"] == 0.6

    r2 = c.put("/api/settings", json={"search_score_threshold": 0.45})
    assert r2.status_code == 200
    assert r2.json()["search_score_threshold"] == 0.45

    path = tmp_path / "settings.json"
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["search_score_threshold"] == 0.45

    settings_module._SETTINGS.clear()
    settings_module._SETTINGS.update(dict(settings_module.DEFAULTS))
    settings_module._merge_file_into_settings()
    assert c.get("/api/settings").json()["search_score_threshold"] == 0.45


def test_settings_api_rejects_search_score_threshold_out_of_range() -> None:
    r = client.put("/api/settings", json={"search_score_threshold": 1.5})
    assert r.status_code == 422


def test_settings_api_delete_models_cache_removes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B08: DELETE /api/settings/models_cache removes the embedding models folder."""
    monkeypatch.setattr(settings_module, "app_config", SimpleNamespace(data_dir=tmp_path))
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "dummy.txt").write_text("x", encoding="utf-8")

    c = TestClient(app)
    r = c.delete("/api/settings/models_cache")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "cleared"
    assert str(models_dir) in body.get("path", "")
    assert not models_dir.exists()


def test_settings_api_delete_models_cache_ok_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B08: deleting a missing cache is idempotent."""
    monkeypatch.setattr(settings_module, "app_config", SimpleNamespace(data_dir=tmp_path))
    c = TestClient(app)
    r = c.delete("/api/settings/models_cache")
    assert r.status_code == 200
    assert r.json().get("status") == "cleared"
