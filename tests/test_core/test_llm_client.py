from unittest.mock import MagicMock, patch

import pytest


def test_llm_client_ollama_mode_sets_native_base_url_and_model() -> None:
    from src.core.llm_client import LLMClient

    client = LLMClient(
        settings={
            "llm_mode": "ollama",
            "ollama_base_url": "http://127.0.0.1:11434/",
            "ollama_model_id": "llama3.2",
        }
    )
    assert client._ollama_base == "http://127.0.0.1:11434"  # noqa: SLF001
    assert client._default_model == "llama3.2"  # noqa: SLF001


def test_llm_client_cloud_passes_api_key_and_optional_base_url() -> None:
    with patch("src.core.llm_client.OpenAI") as mock_openai:
        from src.core.llm_client import LLMClient

        LLMClient(
            settings={
                "llm_mode": "cloud",
                "api_key": "sk-test",
                "api_base_url": "https://api.openai.com/v1",
                "model_id": "gpt-4o",
            }
        )
        mock_openai.assert_called_once()
        kwargs = mock_openai.call_args.kwargs
        assert kwargs["api_key"] == "sk-test"
        assert kwargs["base_url"] == "https://api.openai.com/v1"


def test_llm_client_cloud_omits_base_url_when_empty() -> None:
    with patch("src.core.llm_client.OpenAI") as mock_openai:
        from src.core.llm_client import LLMClient

        LLMClient(
            settings={
                "llm_mode": "cloud",
                "api_key": "sk-test",
                "api_base_url": "",
                "model_id": "gpt-4o",
            }
        )
        kwargs = mock_openai.call_args.kwargs
        assert kwargs["api_key"] == "sk-test"
        assert "base_url" not in kwargs


def test_llm_client_ollama_chat_uses_message_content() -> None:
    from src.core.llm_client import LLMClient

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.status_code = 200
    resp.json.return_value = {"message": {"content": "reply-from-message"}}
    with patch("src.core.llm_client.httpx.get") as mock_get, patch("src.core.llm_client.httpx.post", return_value=resp):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "llama3.2"}]}
        client = LLMClient(settings={"llm_mode": "ollama"})
        out = client.chat_completion([{"role": "user", "content": "Hello"}])
    assert out.choices[0].message.content == "reply-from-message"


def test_llm_client_ollama_uses_response_field_fallback() -> None:
    from src.core.llm_client import LLMClient

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.status_code = 200
    resp.json.return_value = {"response": "reply-from-response"}
    with patch("src.core.llm_client.httpx.get") as mock_get, patch("src.core.llm_client.httpx.post", return_value=resp):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "llama3.2"}]}
        client = LLMClient(settings={"llm_mode": "ollama"})
        out = client.chat_completion([{"role": "user", "content": "Hello"}])
    assert out.choices[0].message.content == "reply-from-response"


def test_llm_client_cloud_default_model_when_unset() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock()

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(settings={"llm_mode": "cloud", "api_key": "k"})
        client.chat_completion([{"role": "user", "content": "x"}])

    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"


def test_llm_client_ollama_raises_clear_error_when_model_missing() -> None:
    from src.core.llm_client import LLMClient

    with patch("src.core.llm_client.httpx.get") as mock_get, patch("src.core.llm_client.httpx.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "qwen2.5:7b"}]}
        client = LLMClient(settings={"llm_mode": "ollama", "ollama_model_id": "llama3.2"})
        with pytest.raises(RuntimeError, match="not available in Ollama"):
            client.chat_completion([{"role": "user", "content": "x"}])
    mock_post.assert_not_called()


def test_llm_client_ollama_logs_raw_response_payload(caplog: pytest.LogCaptureFixture) -> None:
    from src.core.llm_client import LLMClient

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.status_code = 200
    resp.json.return_value = {"message": {"content": "ok"}}
    with patch("src.core.llm_client.httpx.get") as mock_get, patch("src.core.llm_client.httpx.post", return_value=resp):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "llama3.2"}]}
        client = LLMClient(settings={"llm_mode": "ollama"})
        with caplog.at_level("DEBUG"):
            client.chat_completion([{"role": "user", "content": "x"}])
    assert "Ollama raw response body" in caplog.text
