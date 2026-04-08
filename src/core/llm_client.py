from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified chat completion client for Ollama (OpenAI-compatible) and cloud APIs."""

    def __init__(self, settings: dict[str, Any], *, timeout: float | None = None) -> None:
        """Build an OpenAI SDK client from app settings.

        Args:
            settings: Dict with ``llm_mode`` (``ollama`` | ``cloud``), URLs, keys, and model ids.
            timeout: Optional HTTP timeout in seconds (e.g. for connectivity tests).
        """
        self._settings = settings
        mode = settings.get("llm_mode", "ollama")
        client_kwargs: dict[str, Any] = {}
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        if mode == "ollama":
            base = str(settings.get("ollama_base_url", "http://localhost:11434")).rstrip("/")
            self._client = OpenAI(base_url=f"{base}/v1", api_key="ollama", **client_kwargs)
            self._default_model = settings.get("ollama_model_id", "llama3.2")
        else:
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
        """Run a chat completion with the configured provider.

        Args:
            messages: OpenAI-style chat messages.
            stream: If True, returns a streaming iterator.
            model: Override default model from settings.
            max_tokens: Override; defaults to settings ``max_tokens`` or 2048.
            temperature: Override; defaults to settings ``temperature`` or 0.3.
            **kwargs: Extra arguments passed to ``chat.completions.create``.

        Returns:
            Completion response or stream from the OpenAI SDK.
        """
        mt = max_tokens if max_tokens is not None else self._settings.get("max_tokens", 2048)
        temp = temperature if temperature is not None else self._settings.get("temperature", 0.3)
        return self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            stream=stream,
            max_tokens=mt,
            temperature=temp,
            **kwargs,
        )
