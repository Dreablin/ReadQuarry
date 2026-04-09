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
    assert "count" in body
    assert isinstance(body["count"], int)
    # B01: count is total appends (monotonic), not only current buffer length (ring may drop old rows).
    assert body["count"] >= len(body["entries"])


def test_logs_api_count_increments_on_each_new_log() -> None:
    """B01: change detection must fire when new lines are appended even if buffer length is capped."""
    client = TestClient(app)
    before = client.get("/api/logs").json()["count"]
    log = logging.getLogger("test_logs_api_count_increment")
    log.info("readquarry-count-increment-marker")
    after = client.get("/api/logs").json()["count"]
    assert after > before


def test_logs_api_count_advances_when_ring_buffer_wraps() -> None:
    """B01: after maxlen, len(entries) stays capped but count keeps increasing."""
    client = TestClient(app)
    before = client.get("/api/logs").json()["count"]
    spam = logging.getLogger("test_logs_api_ring_wrap")
    for i in range(505):
        spam.info("readquarry-ring-wrap-%d", i)
    body = client.get("/api/logs").json()
    assert len(body["entries"]) <= 500
    assert body["count"] - before >= 505


def test_logs_api_includes_recent_log_records() -> None:
    client = TestClient(app)
    log = logging.getLogger("test_logs_api_marker")
    log.info("readquarry-test-log-marker-unique-b10")
    response = client.get("/api/logs")
    assert response.status_code == 200
    messages = " ".join(e.get("message", "") for e in response.json()["entries"])
    assert "readquarry-test-log-marker-unique-b10" in messages
