from __future__ import annotations

import hashlib
import random

from config import settings

# Multilingual MiniLM (384-dim): Russian, English, and 50+ other languages.
DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


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
        if self._allow_fallback:
            try:
                from sentence_transformers import SentenceTransformer

                return SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    cache_folder=self._cache_folder,
                )
            except Exception:
                return None
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(
            self.model_name,
            device=self.device,
            cache_folder=self._cache_folder,
        )

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
