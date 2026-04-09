from __future__ import annotations

import hashlib
import logging
import os
import random
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from config import settings

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# Multilingual MiniLM (384-dim): Russian, English, and 50+ other languages.
DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def _hf_hub_models_dirname(model_name: str) -> str:
    """Directory name used by Hugging Face Hub cache for a model id."""
    if "/" in model_name:
        return "models--" + model_name.replace("/", "--")
    return f"models--sentence-transformers--{model_name}"


def _dir_contains_any_file(path: Path) -> bool:
    """True if ``path`` is a directory that contains at least one file."""
    if not path.is_dir():
        return False
    for p in path.rglob("*"):
        if p.is_file():
            return True
    return False


def _embedding_model_files_present(cache_root: Path, model_name: str) -> bool:
    """Return True if a full model download appears present under ``cache_root``."""
    candidates = (
        cache_root / "sentence-transformers" / model_name,
        cache_root / model_name,
        cache_root / _hf_hub_models_dirname(model_name),
    )
    for cand in candidates:
        if _dir_contains_any_file(cand):
            return True
    return False


def _with_hf_hub_offline(fn: Callable[[], _T]) -> _T:
    """Set ``HF_HUB_OFFLINE=1`` for the duration of ``fn`` and restore prior env."""
    previous = os.environ.get("HF_HUB_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        return fn()
    finally:
        if previous is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous


class EmbeddingService:
    """Compute text embeddings via ``sentence_transformers``.

    By default the model must load successfully; missing dependencies raise
    ``ImportError`` instead of silently using random vectors (see BUGS.md B02).

    Set ``allow_fallback=True`` only in tests or tooling that must run without
    the ML stack; that path uses deterministic pseudo-vectors of the right length.

    Downloaded models are stored under ``{data_dir}/models`` (see ``cache_folder``),
    defaulting to ``config.settings.data_dir``.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        device: str = "cpu",
        *,
        allow_fallback: bool = False,
        cache_folder: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.dimension = 384
        self._allow_fallback = allow_fallback
        self._cache_folder = cache_folder if cache_folder is not None else str(settings.data_dir / "models")
        self._model = self._load_model()

    def _load_model(self):  # type: ignore[no-untyped-def]
        cache_root = Path(self._cache_folder)
        local_only = _embedding_model_files_present(cache_root, self.model_name)
        if local_only:
            logger.debug(
                "Embedding model cache hit under %s; loading with local_files_only=True",
                cache_root,
            )

        def _instantiate(*, offline: bool) -> object:
            from sentence_transformers import SentenceTransformer

            kwargs: dict[str, object] = {
                "device": self.device,
                "cache_folder": self._cache_folder,
            }
            if offline:
                kwargs["local_files_only"] = True
            return SentenceTransformer(self.model_name, **kwargs)

        if self._allow_fallback:
            try:
                if local_only:
                    return _with_hf_hub_offline(lambda: _instantiate(offline=True))
                return _instantiate(offline=False)
            except Exception:
                return None

        if local_only:
            return _with_hf_hub_offline(lambda: _instantiate(offline=True))
        return _instantiate(offline=False)

    def _fallback_embed(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        return [round(rng.uniform(-1.0, 1.0), 8) for _ in range(self.dimension)]

    def embed_text(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if self._model is None:
            return self._fallback_embed(text)
        vector = self._model.encode(text)
        return [float(v) for v in vector]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list):
            raise TypeError("texts must be a list of strings")
        if any(not isinstance(text, str) for text in texts):
            raise TypeError("texts must be a list of strings")
        if self._model is None:
            return [self._fallback_embed(text) for text in texts]
        vectors = self._model.encode(texts)
        return [[float(v) for v in row] for row in vectors]
