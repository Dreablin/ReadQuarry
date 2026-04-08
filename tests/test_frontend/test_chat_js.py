"""Structural checks for the chat panel component (static/js/components/chat.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHAT_JS = ROOT / "static" / "js" / "components" / "chat.js"


@pytest.fixture(scope="module")
def chat_js() -> str:
    return CHAT_JS.read_text(encoding="utf-8")


def test_chat_js_exists() -> None:
    assert CHAT_JS.is_file(), "static/js/components/chat.js must exist"


def test_chat_js_imports_api(chat_js: str) -> None:
    assert "export " in chat_js
    assert 'from "../api.js"' in chat_js or "from '../api.js'" in chat_js
    assert "sendChatMessage" in chat_js
    assert "getChatMessages" in chat_js


def test_chat_js_exports_init(chat_js: str) -> None:
    assert "initChat" in chat_js


def test_chat_js_shell_ids(chat_js: str) -> None:
    assert "chat-messages" in chat_js
    assert "chat-form" in chat_js
    assert "message-input" in chat_js
    assert "send-button" in chat_js


def test_chat_js_typing_indicator(chat_js: str) -> None:
    assert "typing-indicator" in chat_js


def test_chat_js_sse_streaming(chat_js: str) -> None:
    lower = chat_js.lower()
    assert "getreader" in lower or "getReader" in chat_js
    assert "data:" in chat_js or '"delta"' in chat_js


def test_chat_js_sse_logs_malformed_json(chat_js: str) -> None:
    """B04: malformed SSE lines must not fail silently."""
    assert "console.warn" in chat_js
    assert "failed to parse" in chat_js.lower()


def test_chat_js_delta_accepts_string_content_including_empty(chat_js: str) -> None:
    """B04: use typeof ev.content === ''string'' so empty deltas and placeholders render."""
    assert 'typeof ev.content === "string"' in chat_js


def test_chat_js_message_roles(chat_js: str) -> None:
    lower = chat_js.lower()
    assert "user" in lower and ("assistant" in lower or "role" in lower)


def test_chat_js_render_or_append_message(chat_js: str) -> None:
    lower = chat_js.lower()
    assert "message" in lower and ("append" in lower or "render" in lower or "createelement" in lower)
