from unittest.mock import MagicMock, patch

import pytest


def test_llm_client_ollama_uses_openai_compatible_base_url() -> None:
    with patch("src.core.llm_client.OpenAI") as mock_openai:
        from src.core.llm_client import LLMClient

        LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://localhost:11434",
                "ollama_model_id": "llama3.2",
            }
        )
        mock_openai.assert_called_once()
        kwargs = mock_openai.call_args.kwargs
        assert kwargs["base_url"] == "http://localhost:11434/v1"
        assert kwargs["api_key"] == "ollama"


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


def test_llm_client_chat_completion_forwards_messages() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="reply"))]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://localhost:11434",
                "ollama_model_id": "mistral",
                "max_tokens": 100,
                "temperature": 0.5,
            }
        )
        messages = [{"role": "user", "content": "Hello"}]
        out = client.chat_completion(messages)

    mock_client.chat.completions.create.assert_called_once()
    call_kw = mock_client.chat.completions.create.call_args.kwargs
    assert call_kw["messages"] == messages
    assert call_kw["model"] == "mistral"
    assert call_kw["max_tokens"] == 100
    assert call_kw["temperature"] == 0.5
    assert out == mock_response


def test_llm_client_ollama_default_model_when_unset() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock()

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(settings={"llm_mode": "ollama"})
        client.chat_completion([{"role": "user", "content": "x"}])

    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "llama3.2"


def test_llm_client_cloud_default_model_when_unset() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock()

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(settings={"llm_mode": "cloud", "api_key": "k"})
        client.chat_completion([{"role": "user", "content": "x"}])

    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"


def test_llm_client_ollama_strips_trailing_slash_from_base_url() -> None:
    with patch("src.core.llm_client.OpenAI") as mock_openai:
        from src.core.llm_client import LLMClient

        LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://127.0.0.1:11434/",
            }
        )
        assert mock_openai.call_args.kwargs["base_url"] == "http://127.0.0.1:11434/v1"


def test_llm_client_chat_completion_forwards_stream_flag() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter(())

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://localhost:11434",
                "ollama_model_id": "m",
            }
        )
        client.chat_completion([{"role": "user", "content": "x"}], stream=True)

    assert mock_client.chat.completions.create.call_args.kwargs["stream"] is True


def test_llm_client_chat_completion_explicit_overrides_settings() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock()

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://localhost:11434",
                "ollama_model_id": "base-model",
                "max_tokens": 500,
                "temperature": 0.1,
            }
        )
        client.chat_completion(
            [{"role": "user", "content": "q"}],
            model="override-model",
            max_tokens=50,
            temperature=0.9,
        )

    kw = mock_client.chat.completions.create.call_args.kwargs
    assert kw["model"] == "override-model"
    assert kw["max_tokens"] == 50
    assert kw["temperature"] == 0.9


def test_llm_client_chat_completion_passes_through_extra_create_kwargs() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock()

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://localhost:11434",
                "ollama_model_id": "m",
            }
        )
        client.chat_completion(
            [{"role": "user", "content": "x"}],
            top_p=0.95,
            frequency_penalty=0.2,
        )

    kw = mock_client.chat.completions.create.call_args.kwargs
    assert kw["top_p"] == 0.95
    assert kw["frequency_penalty"] == 0.2


def test_llm_client_chat_completion_propagates_provider_errors() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("upstream failure")

    with patch("src.core.llm_client.OpenAI", return_value=mock_client):
        from src.core.llm_client import LLMClient

        client = LLMClient(
            settings={
                "llm_mode": "ollama",
                "ollama_base_url": "http://localhost:11434",
                "ollama_model_id": "m",
            }
        )
        with pytest.raises(RuntimeError, match="upstream failure"):
            client.chat_completion([{"role": "user", "content": "x"}])
