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
