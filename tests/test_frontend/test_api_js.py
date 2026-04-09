"""Structural checks for the ReadQuarry API client (static/js/api.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_JS = ROOT / "static" / "js" / "api.js"


@pytest.fixture(scope="module")
def api_js() -> str:
    return API_JS.read_text(encoding="utf-8")


def test_api_js_exists() -> None:
    assert API_JS.is_file(), "static/js/api.js must exist"


def test_api_js_is_es_module(api_js: str) -> None:
    assert "export " in api_js


def test_api_js_uses_fetch(api_js: str) -> None:
    assert "fetch(" in api_js


def test_api_js_books_endpoints(api_js: str) -> None:
    assert "/api/books/upload" in api_js
    assert "/api/books" in api_js
    assert "chunks" in api_js


def test_api_js_clear_all_books(api_js: str) -> None:
    """B16: DELETE /api/books clears all books."""
    assert "clearAllBooks" in api_js
    assert "DELETE" in api_js


def test_api_js_search_endpoints(api_js: str) -> None:
    assert "/api/search/semantic" in api_js
    assert "/api/search/exact" in api_js
    assert "/api/search/hybrid" in api_js


def test_api_js_settings_endpoints(api_js: str) -> None:
    assert "/api/settings" in api_js
    assert "reset" in api_js
    assert "test-llm" in api_js


def test_api_js_clear_models_cache(api_js: str) -> None:
    """B08: DELETE /api/settings/models_cache clears downloaded embedding models."""
    assert "clearModelsCache" in api_js
    assert "/api/settings/models_cache" in api_js
    assert "DELETE" in api_js


def test_api_js_chat_endpoints(api_js: str) -> None:
    assert "/api/chat/sessions" in api_js
    assert "messages" in api_js
    assert "message" in api_js


def test_api_js_logs_endpoint(api_js: str) -> None:
    assert "/api/logs" in api_js


def test_api_js_exports_named_functions(api_js: str) -> None:
    for name in (
        "uploadBook",
        "listBooks",
        "getBook",
        "deleteBook",
        "clearAllBooks",
        "getBookChunks",
        "searchSemantic",
        "searchExact",
        "searchHybrid",
        "getSettings",
        "updateSettings",
        "resetSettings",
        "testLlm",
        "clearModelsCache",
        "createChatSession",
        "listChatSessions",
        "getChatMessages",
        "sendChatMessage",
        "fetchLogs",
    ):
        assert name in api_js, f"Expected exported function name {name} in api.js"
