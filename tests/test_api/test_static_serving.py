"""Tests that FastAPI serves the SPA and static assets."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_serves_index_html() -> None:
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "<!DOCTYPE" in text.upper() or "<!doctype" in text.lower()
    assert "ReadQuarry" in text


def test_css_stylesheet_is_served() -> None:
    response = client.get("/css/style.css")
    assert response.status_code == 200
    body = response.text
    assert ":root" in body or "--color" in body


def test_js_app_module_is_served() -> None:
    response = client.get("/js/app.js")
    assert response.status_code == 200
    assert "initApp" in response.text


def test_api_routes_still_work_after_static_mount() -> None:
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert "llm_mode" in r.json()


def test_health_endpoint_still_works() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_static_dir_matches_repo_layout() -> None:
    from config import settings

    assert settings.static_dir.is_dir()
    assert (settings.static_dir / "index.html").is_file()
