"""Structural checks for log viewer (static/js/components/log-viewer.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LOG_VIEWER_JS = ROOT / "static" / "js" / "components" / "log-viewer.js"


@pytest.fixture(scope="module")
def log_viewer_js() -> str:
    return LOG_VIEWER_JS.read_text(encoding="utf-8")


def test_log_viewer_js_exists() -> None:
    assert LOG_VIEWER_JS.is_file()


def test_log_viewer_js_exports_init(log_viewer_js: str) -> None:
    assert "export " in log_viewer_js
    assert "initLogViewer" in log_viewer_js


def test_log_viewer_js_uses_logs_api(log_viewer_js: str) -> None:
    assert "fetchLogs" in log_viewer_js or "/api/logs" in log_viewer_js


def test_log_viewer_tracks_last_count_and_skips_noop_updates(log_viewer_js: str) -> None:
    """B01: avoid replacing DOM when count hasn't changed."""
    assert "lastCount" in log_viewer_js
    assert "data?.count" in log_viewer_js or "entries.length" in log_viewer_js
    assert "if (count === lastCount)" in log_viewer_js


def test_log_viewer_b07_requires_tag_filter_select(log_viewer_js: str) -> None:
    """B07: initLogViewer requires #log-filter-tag for filtering."""
    assert "log-filter-tag" in log_viewer_js
    assert "HTMLSelectElement" in log_viewer_js


def test_log_viewer_b07_merge_tag_options_additive(log_viewer_js: str) -> None:
    """B07: merge API tags into dropdown without removing existing options."""
    assert "mergeTagOptions" in log_viewer_js
    assert "appendChild" in log_viewer_js
    assert "have.has" in log_viewer_js or "have.add" in log_viewer_js


def test_log_viewer_b07_filters_when_not_all(log_viewer_js: str) -> None:
    """B07: entries are filtered by tag when select value is not ALL."""
    assert 'filterVal !== "ALL"' in log_viewer_js
    assert "e.tag" in log_viewer_js
    assert "applyFilterAndRender" in log_viewer_js


def test_log_viewer_b07_change_listener_re_renders(log_viewer_js: str) -> None:
    """B07: changing the filter immediately re-renders from cached entries."""
    assert 'addEventListener("change"' in log_viewer_js
    assert "lastEntries" in log_viewer_js
