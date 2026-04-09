from __future__ import annotations

import json
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
            return self._ollama_chat(messages, model=model, temperature=temp)

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
        temperature: float = 0.3,
    ) -> _OllamaResponse:
        """Call Ollama's native ``/api/chat`` endpoint."""
        model_name = str(model or self._default_model)
        logger.info("Ollama request model=%s", model_name)
        self._validate_ollama_model_exists(model_name)

        # Omit ``num_predict`` here: some Ollama models (e.g. Qwen with thinking) return
        # empty ``message.content`` when ``num_predict`` is set in ``options``, while the
        # assistant text only appears under ``thinking``. Temperature still applies.
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        timeout = self._timeout or 120.0
        url = f"{self._ollama_base}/api/chat"
        logger.info("Ollama request url=%s model=%s", url, model_name)

        resp = httpx.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        logger.debug("Ollama response status=%s", resp.status_code)
        data = resp.json()
        logger.debug("Ollama raw response body: %s", json.dumps(data, ensure_ascii=False)[:2000])

        content = ""
        msg = data.get("message")
        if isinstance(msg, dict):
            content = str(msg.get("content", "") or "")
            if content:
                logger.debug("Ollama content extracted from message.content")
        if not content:
            fallback = data.get("response")
            if isinstance(fallback, str) and fallback:
                content = fallback
                logger.debug("Ollama content extracted from response fallback")

        logger.info("Ollama response chars=%d", len(content))
        return _OllamaResponse(content=content)

    def _validate_ollama_model_exists(self, model_name: str) -> None:
        """Best-effort model availability check for clearer errors."""
        timeout = min(float(self._timeout or 120.0), 10.0)
        tags_url = f"{self._ollama_base}/api/tags"
        try:
            resp = httpx.get(tags_url, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning("Could not validate Ollama model via %s: %s", tags_url, exc)
            return

        models = payload.get("models")
        if not isinstance(models, list):
            return
        names = {
            str(item.get("name"))
            for item in models
            if isinstance(item, dict) and item.get("name")
        }
        if names and model_name not in names:
            available = ", ".join(sorted(names))
            raise RuntimeError(
                f"Model '{model_name}' is not available in Ollama. Available models: {available}"
            )
