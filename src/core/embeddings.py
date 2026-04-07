from __future__ import annotations

import hashlib
import random


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self.dimension = 384
        self._model = self._load_model()

    def _load_model(self):  # type: ignore[no-untyped-def]
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(self.model_name, device=self.device)
        except Exception:
            # Keep local development/test flow stable even if model deps are unavailable.
            return None

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
