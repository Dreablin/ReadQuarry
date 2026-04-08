"""Tests for in-memory log ring buffer API (B10)."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from main import app


def test_logs_api_get_returns_entries_list() -> None:
    client = TestClient(app)
    response = client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    assert "entries" in body
    assert isinstance(body["entries"], list)


def test_logs_api_includes_recent_log_records() -> None:
    client = TestClient(app)
    log = logging.getLogger("test_logs_api_marker")
    log.info("readquarry-test-log-marker-unique-b10")
    response = client.get("/api/logs")
    assert response.status_code == 200
    messages = " ".join(e.get("message", "") for e in response.json()["entries"])
    assert "readquarry-test-log-marker-unique-b10" in messages
