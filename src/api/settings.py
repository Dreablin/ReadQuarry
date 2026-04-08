from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator, model_validator

from config import settings as app_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


DEFAULTS: dict[str, object] = {
    "llm_mode": "ollama",  # "ollama" | "cloud"
    "ollama_base_url": "http://localhost:11434",
    "ollama_model_id": "llama3.2",
    "provider": "openai",
    "api_key": "",
    "api_base_url": "",
    "model_id": "gpt-4o",
    "max_tokens": 2048,
    "temperature": 0.3,
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_device": "cpu",
    "semantic_top_k": 5,
    "exact_results": 5,
    "final_context_chunks": 7,
}

_SETTINGS: dict[str, object] = dict(DEFAULTS)


def _persist_path() -> Path:
    return Path(app_config.data_dir) / "settings.json"


def _save_to_disk() -> None:
    path = _persist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(_SETTINGS), indent=2, ensure_ascii=False), encoding="utf-8")


def _merge_file_into_settings() -> None:
    """Overlay values from settings.json onto in-memory settings (only known keys)."""
    path = _persist_path()
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load settings file %s: %s", path, exc)
        return
    if not isinstance(raw, dict):
        return
    for key in DEFAULTS:
        if key in raw:
            _SETTINGS[key] = raw[key]


# Load persisted settings on import (after defaults exist).
_merge_file_into_settings()


class SettingsUpdate(BaseModel):
    llm_mode: str | None = Field(default=None, pattern="^(ollama|cloud)$")
    ollama_base_url: str | None = None
    ollama_model_id: str | None = None

    provider: str | None = None
    api_key: str | None = None
    api_base_url: str | None = None
    model_id: str | None = None
    max_tokens: int | None = Field(default=None, gt=0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)

    embedding_model: str | None = None
    embedding_device: str | None = Field(default=None, pattern="^(cpu|cuda)$")

    semantic_top_k: int | None = Field(default=None, gt=0)
    exact_results: int | None = Field(default=None, gt=0)
    final_context_chunks: int | None = Field(default=None, gt=0)

    @field_validator("ollama_base_url", "api_base_url", mode="before")
    @classmethod
    def validate_http_urls(cls, value: object) -> object:
        if value is None or value == "":
            return value
        text = str(value).strip()
        parsed = urlparse(text)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Must be a valid http(s) URL with host")
        return text

    @model_validator(mode="after")
    def validate_cloud_requires_key(self):
        if self.llm_mode == "cloud":
            if (self.api_key is None) or (self.api_key.strip() == ""):
                raise ValueError("api_key is required when llm_mode is cloud")
        return self


@router.get("")
def get_settings() -> dict:
    return dict(_SETTINGS)


@router.put("")
def update_settings(payload: SettingsUpdate) -> dict:
    data = payload.model_dump(exclude_none=True)
    _SETTINGS.update(data)
    _save_to_disk()
    return dict(_SETTINGS)


@router.post("/reset")
def reset_settings() -> dict:
    _SETTINGS.clear()
    _SETTINGS.update(DEFAULTS)
    _save_to_disk()
    return dict(_SETTINGS)


@router.post("/test-llm")
def test_llm() -> dict:
    # Placeholder: real connectivity test comes with LLM client integration.
    return {"status": "ok"}
