from unittest.mock import MagicMock, patch


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
