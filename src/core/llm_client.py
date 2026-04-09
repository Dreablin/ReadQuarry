from __future__ import annotations

import logging
from typing import Any

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)


class _OllamaMessage:
    """Minimal wrapper matching ``openai.ChatCompletionMessage`` interface."""

    def __init__(self, content: str) -> None:
        self.content = content


class _OllamaChoice:
    """Minimal wrapper matching ``openai.Choice`` interface."""

    def __init__(self, content: str) -> None:
        self.message = _OllamaMessage(content)


class _OllamaResponse:
    """Minimal wrapper matching ``openai.ChatCompletion`` interface."""

    def __init__(self, content: str) -> None:
        self.choices = [_OllamaChoice(content)]


class LLMClient:
    """Chat completion client: native Ollama API for local models, OpenAI SDK for cloud."""

    def __init__(self, settings: dict[str, Any], *, timeout: float | None = None) -> None:
        self._settings = settings
        self._mode = settings.get("llm_mode", "ollama")
        self._timeout = timeout

        if self._mode == "ollama":
            base = str(settings.get("ollama_base_url", "http://localhost:11434")).rstrip("/")
            self._ollama_base = base
            self._default_model = settings.get("ollama_model_id", "llama3.2")
        else:
            client_kwargs: dict[str, Any] = {}
            if timeout is not None:
                client_kwargs["timeout"] = timeout
            api_key = settings.get("api_key") or ""
            base_url = settings.get("api_base_url") or None
            kwargs: dict[str, Any] = {"api_key": api_key, **client_kwargs}
            if base_url:
                kwargs["base_url"] = str(base_url).rstrip("/")
            self._client = OpenAI(**kwargs)
            self._default_model = settings.get("model_id", "gpt-4o")

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        stream: bool = False,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run a chat completion.

        For Ollama mode, calls the native ``/api/chat`` endpoint directly via
        httpx (bypasses the OpenAI SDK whose SSE parser is incompatible with
        some Ollama versions). Returns a lightweight wrapper with the same
        ``.choices[0].message.content`` interface.

        For cloud mode, delegates to the OpenAI SDK as before.
        """
        mt = max_tokens if max_tokens is not None else self._settings.get("max_tokens", 2048)
        temp = temperature if temperature is not None else self._settings.get("temperature", 0.3)

        if self._mode == "ollama":
            return self._ollama_chat(messages, model=model, num_predict=mt, temperature=temp)

        return self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            stream=stream,
            max_tokens=mt,
            temperature=temp,
            **kwargs,
        )

    def _ollama_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        num_predict: int = 2048,
        temperature: float = 0.3,
    ) -> _OllamaResponse:
        """Call Ollama's native ``/api/chat`` endpoint."""
        payload: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "temperature": temperature,
            },
        }
        timeout = self._timeout or 120.0
        url = f"{self._ollama_base}/api/chat"
        logger.info("Ollama request url=%s model=%s", url, payload["model"])

        resp = httpx.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        content = ""
        msg = data.get("message")
        if isinstance(msg, dict):
            content = msg.get("content", "")

        logger.info("Ollama response chars=%d", len(content))
        return _OllamaResponse(content=content)
