"""Tests for in-memory log ring buffer API (B10)."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from main import app
from src.api import logs as logs_module


def test_logs_api_get_returns_entries_list() -> None:
    client = TestClient(app)
    response = client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    assert "entries" in body
    assert isinstance(body["entries"], list)
    assert "count" in body
    assert isinstance(body["count"], int)
    assert "tags" in body
    assert isinstance(body["tags"], list)
    assert body["tags"] == sorted(body["tags"])
    assert len(body["tags"]) == len(set(body["tags"]))
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


def test_logs_api_b04_entry_defaults_tag_to_info() -> None:
    """B04: logs without ``extra`` get tag INFO on each API entry."""
    client = TestClient(app)
    marker = "readquarry-b04-default-tag-info-xyz"
    log = logging.getLogger("test_logs_api_b04_default")
    log.info(marker)
    body = client.get("/api/logs").json()
    matches = [e for e in body["entries"] if marker in e.get("message", "")]
    assert matches
    assert all(e.get("tag") == "INFO" for e in matches)


def test_logs_api_b04_extra_tag_propagates() -> None:
    """B04: ``logger.info(..., extra={"tag": "LLM"})`` appears on the API entry."""
    client = TestClient(app)
    marker = "readquarry-b04-extra-llm-abc"
    log = logging.getLogger("test_logs_api_b04_llm")
    log.info(marker, extra={"tag": "LLM"})
    body = client.get("/api/logs").json()
    matches = [e for e in body["entries"] if marker in e.get("message", "")]
    assert matches
    assert matches[-1].get("tag") == "LLM"


def test_logs_api_b04_tags_list_is_sorted_distinct_union() -> None:
    """B04: response ``tags`` is sorted unique tags present in the buffer."""
    client = TestClient(app)
    log = logging.getLogger("test_logs_api_b04_tags_union")
    log.info("readquarry-b04-t1", extra={"tag": "TIME"})
    logs_module.log_with_tag(log, logging.WARNING, "ZZZ", "readquarry-b04-t2 %s", "x")
    log.info("readquarry-b04-t3", extra={"tag": "LLM"})
    body = client.get("/api/logs").json()
    assert "TIME" in body["tags"]
    assert "LLM" in body["tags"]
    assert "ZZZ" in body["tags"]
    assert body["tags"] == sorted(body["tags"])
    assert len(body["tags"]) == len(set(body["tags"]))


def test_logs_api_b04_log_with_tag_helper() -> None:
    """B04: ``log_with_tag`` records the given tag on the ring-buffer row."""
    client = TestClient(app)
    marker = "readquarry-b04-helper-marker"
    log = logging.getLogger("test_logs_api_b04_helper")
    logs_module.log_with_tag(log, logging.INFO, "TIME", marker)
    body = client.get("/api/logs").json()
    matches = [e for e in body["entries"] if marker in e.get("message", "")]
    assert matches[-1]["tag"] == "TIME"
