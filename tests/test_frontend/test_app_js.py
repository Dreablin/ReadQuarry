"""Structural checks for the app controller (static/js/app.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static" / "js" / "app.js"


@pytest.fixture(scope="module")
def app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_app_js_exists() -> None:
    assert APP_JS.is_file(), "static/js/app.js must exist"


def test_app_js_is_es_module(app_js: str) -> None:
    assert "import " in app_js
    assert "export " in app_js


def test_app_js_imports_components(app_js: str) -> None:
    assert "book-list.js" in app_js
    assert "book-upload.js" in app_js
    assert "chat.js" in app_js
    assert "references.js" in app_js
    assert "settings.js" in app_js
    assert "log-viewer.js" in app_js


def test_app_js_imports_api(app_js: str) -> None:
    assert 'from "./api.js"' in app_js or "from './api.js'" in app_js
    assert "createChatSession" in app_js


def test_app_js_book_select_creates_new_chat_session_not_list_reuse(app_js: str) -> None:
    """B02: each book selection starts a new session; do not reuse newest from listChatSessions."""
    assert "ensureSession" not in app_js
    assert "listChatSessions" not in app_js
    assert "createChatSession" in app_js
    assert "book_id: bookId" in app_js or "book_id:bookId" in app_js.replace(" ", "")


def test_app_js_exports_init_app(app_js: str) -> None:
    assert "initApp" in app_js


def test_app_js_wires_book_session_or_chat(app_js: str) -> None:
    lower = app_js.lower()
    assert "session" in lower or "chatsession" in lower.replace(" ", "")


def test_app_js_search_or_view_routing(app_js: str) -> None:
    lower = app_js.lower()
    assert "search" in lower and ("view" in lower or "discuss" in lower or "route" in lower)
    assert "main-nav-discussion" in app_js
    assert "main-nav-search" in app_js
    assert "main-nav-logs" in app_js


def test_app_js_set_view_uses_view_hidden_class(app_js: str) -> None:
    """B17: Toggle visibility with .view--hidden so author CSS cannot override [hidden]."""
    assert "view--hidden" in app_js
    assert "classList.toggle" in app_js
    assert ".hidden =" not in app_js


def test_app_js_search_hybrid_passes_result_limits(app_js: str) -> None:
    """B05: search submits semantic_k, exact_k, final_n from Max results control."""
    assert "search-max-results" in app_js
    assert "semantic_k" in app_js
    assert "exact_k" in app_js
    assert "final_n" in app_js


def test_app_js_chat_on_done_passes_scores_to_references(app_js: str) -> None:
    """B06: initChat onDone passes scores into appendReferencedChunkIds."""
    assert "appendReferencedChunkIds" in app_js
    assert "onDone:" in app_js
    assert "appendReferencedChunkIds(bid, ids, scores)" in app_js


def test_app_js_wires_clear_chat_button(app_js: str) -> None:
    """B07: Clear Chat creates a new session, clears messages and references."""
    assert "clear-chat" in app_js
    assert "New conversation started" in app_js
    assert "refs.clear()" in app_js
    assert "createChatSession" in app_js
    assert "clearMessages()" in app_js
