"""Tests for global API exception handlers (T40)."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api.exception_handlers import register_exception_handlers


def test_register_handlers_maps_unexpected_errors_to_safe_500() -> None:
    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("internal_secret_token_do_not_expose")

    register_exception_handlers(app)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "internal_secret" not in str(data).lower()


def test_register_handlers_maps_http_exception_detail() -> None:
    app = FastAPI()

    @app.get("/gone")
    async def gone() -> None:
        raise HTTPException(status_code=410, detail="This resource is no longer available.")

    register_exception_handlers(app)
    client = TestClient(app)
    response = client.get("/gone")
    assert response.status_code == 410
    assert response.json() == {"detail": "This resource is no longer available."}


def test_main_app_registers_global_handlers() -> None:
    from main import app

    assert Exception in app.exception_handlers
    assert len(app.exception_handlers) >= 1
