from src.core.embeddings import EmbeddingService


def test_embedding_service_single_text_shape() -> None:
    service = EmbeddingService()
    vector = service.embed_text("hello world")
    assert isinstance(vector, list)
    assert len(vector) == 384


def test_embedding_service_batch_shape() -> None:
    service = EmbeddingService()
    vectors = service.embed_texts(["alpha", "beta", "gamma"])
    assert len(vectors) == 3
    assert all(len(v) == 384 for v in vectors)


def test_embedding_service_is_deterministic_for_same_text() -> None:
    service = EmbeddingService()
    v1 = service.embed_text("same input")
    v2 = service.embed_text("same input")
    assert v1 == v2


def test_embedding_service_rejects_non_string_input() -> None:
    service = EmbeddingService()
    try:
        service.embed_text(123)  # type: ignore[arg-type]
        raised = False
    except TypeError:
        raised = True
    assert raised is True


def test_embedding_service_handles_empty_batch() -> None:
    service = EmbeddingService()
    vectors = service.embed_texts([])
    assert vectors == []
