"""Integration tests for LLMClient against a local Ollama instance (B07).

When Ollama is not running, the module skips so CI and offline runs stay green.
"""

from __future__ import annotations

import pytest

OLLAMA_BASE_URL = "http://localhost:11434"


def _ollama_reachable() -> bool:
    try:
        import httpx

        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        return r.status_code == 200
    except Exception:
        return False


if not _ollama_reachable():
    pytest.skip("Ollama is not running", allow_module_level=True)


def _tagged_model_names() -> list[str]:
    import httpx

    r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
    r.raise_for_status()
    out: list[str] = []
    for m in r.json().get("models") or []:
        if isinstance(m, dict):
            name = m.get("name")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


def _pick_ollama_model_name() -> str:
    """Prefer a running model from /api/ps that also appears in /api/tags (exact name)."""
    import httpx

    tagged = set(_tagged_model_names())
    if not tagged:
        pytest.skip("No Ollama models available")

    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=5.0)
        r.raise_for_status()
        for m in r.json().get("models") or []:
            if isinstance(m, dict):
                name = m.get("name")
                if isinstance(name, str) and name.strip() in tagged:
                    return name.strip()
    except Exception:
        pass

    return sorted(tagged)[0]


@pytest.fixture(scope="module")
def ollama_model() -> str:
    return _pick_ollama_model_name()


@pytest.mark.integration
def test_ollama_chat_completion_returns_non_empty_content(ollama_model: str) -> None:
    """B07: real Ollama round-trip yields non-empty assistant text."""
    from src.core.llm_client import LLMClient

    client = LLMClient(
        {
            "llm_mode": "ollama",
            "ollama_base_url": OLLAMA_BASE_URL,
            "ollama_model_id": ollama_model,
            "max_tokens": 64,
            "temperature": 0.3,
        },
        timeout=180.0,
    )
    response = client.chat_completion([{"role": "user", "content": "What can you do?"}])
    content = response.choices[0].message.content
    assert isinstance(content, str)
    assert content.strip() != ""


@pytest.mark.integration
def test_ollama_chat_completion_response_structure(ollama_model: str) -> None:
    """B07: wrapper exposes OpenAI-like choices/message/content."""
    from src.core.llm_client import LLMClient

    client = LLMClient(
        {
            "llm_mode": "ollama",
            "ollama_base_url": OLLAMA_BASE_URL,
            "ollama_model_id": ollama_model,
            "max_tokens": 32,
            "temperature": 0.3,
        },
        timeout=180.0,
    )
    response = client.chat_completion([{"role": "user", "content": "Say hi in one word."}])
    assert hasattr(response, "choices")
    assert response.choices
    msg = response.choices[0].message
    assert msg is not None
    assert hasattr(msg, "content")
    assert isinstance(msg.content, str)
