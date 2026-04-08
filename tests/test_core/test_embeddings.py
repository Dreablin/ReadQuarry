import builtins
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.core.embeddings as embeddings_module
from src.core.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingService


def test_embedding_service_passes_cache_folder_to_sentence_transformer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """B07: SentenceTransformer receives cache_folder under project data directory."""
    monkeypatch.setattr(embeddings_module, "settings", SimpleNamespace(data_dir=tmp_path))
    captured: dict[str, str | None] = {}

    def fake_st(
        model_name: str,
        *,
        device: str = "cpu",
        cache_folder: str | None = None,
        **kwargs: object,
    ) -> MagicMock:
        captured["cache_folder"] = cache_folder
        mock = MagicMock()
        mock.encode = lambda x: [[0.1] * 384] if isinstance(x, list) else [0.1] * 384
        return mock

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", fake_st)
    _ = embeddings_module.EmbeddingService()
    assert captured["cache_folder"] == str(tmp_path / "models")


def test_embedding_service_raises_import_error_without_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    """B02: do not silently use random vectors when the ML stack is missing."""

    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict | None = None,
        locals: dict | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ):
        if name == "sentence_transformers" or name.startswith("sentence_transformers."):
            raise ImportError("No module named 'sentence_transformers'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with pytest.raises(ImportError):
        EmbeddingService()


def test_embedding_service_allow_fallback_uses_deterministic_vectors_when_model_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional test path: explicit flag keeps deterministic stub vectors."""
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict | None = None,
        locals: dict | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ):
        if name == "sentence_transformers" or name.startswith("sentence_transformers."):
            raise ImportError("No module named 'sentence_transformers'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    svc = EmbeddingService(allow_fallback=True)
    v = svc.embed_text("hello")
    assert len(v) == 384
    assert v == svc.embed_text("hello")


def test_default_embedding_model_is_multilingual() -> None:
    """B05: default model must support Russian and English (not English-only MiniLM)."""
    pytest.importorskip("sentence_transformers", reason="embedding model integration")
    assert DEFAULT_EMBEDDING_MODEL == "paraphrase-multilingual-MiniLM-L12-v2"
    assert EmbeddingService().model_name == DEFAULT_EMBEDDING_MODEL


def test_embedding_service_single_text_shape() -> None:
    pytest.importorskip("sentence_transformers", reason="embedding model integration")
    service = EmbeddingService()
    vector = service.embed_text("hello world")
    assert isinstance(vector, list)
    assert len(vector) == 384


def test_embedding_service_batch_shape() -> None:
    pytest.importorskip("sentence_transformers", reason="embedding model integration")
    service = EmbeddingService()
    vectors = service.embed_texts(["alpha", "beta", "gamma"])
    assert len(vectors) == 3
    assert all(len(v) == 384 for v in vectors)


def test_embedding_service_is_deterministic_for_same_text() -> None:
    pytest.importorskip("sentence_transformers", reason="embedding model integration")
    service = EmbeddingService()
    v1 = service.embed_text("same input")
    v2 = service.embed_text("same input")
    assert v1 == v2


def test_embedding_service_rejects_non_string_input() -> None:
    pytest.importorskip("sentence_transformers", reason="embedding model integration")
    service = EmbeddingService()
    try:
        service.embed_text(123)  # type: ignore[arg-type]
        raised = False
    except TypeError:
        raised = True
    assert raised is True


def test_embedding_service_handles_empty_batch() -> None:
    pytest.importorskip("sentence_transformers", reason="embedding model integration")
    service = EmbeddingService()
    vectors = service.embed_texts([])
    assert vectors == []
