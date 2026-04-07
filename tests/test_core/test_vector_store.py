from pathlib import Path

from src.core.vector_store import VectorStore


def test_vector_store_create_collection() -> None:
    store = VectorStore(persist_directory="data/chroma_test_create")
    name = "book_1"
    collection = store.create_collection(name)
    assert collection is not None
    assert collection.name == name


def test_vector_store_add_and_query_documents() -> None:
    store = VectorStore(persist_directory="data/chroma_test_query")
    name = "book_2"
    store.create_collection(name)
    store.add_documents(
        collection_name=name,
        ids=["1", "2"],
        embeddings=[[0.1] * 384, [0.2] * 384],
        documents=["alpha text", "beta text"],
        metadatas=[{"book_id": 2}, {"book_id": 2}],
    )
    result = store.query(collection_name=name, query_embedding=[0.1] * 384, n_results=1)
    assert "ids" in result
    assert len(result["ids"][0]) == 1


def test_vector_store_delete_collection() -> None:
    store = VectorStore(persist_directory="data/chroma_test_delete")
    name = "book_3"
    store.create_collection(name)
    store.delete_collection(name)
    collections = [c.name for c in store.list_collections()]
    assert name not in collections


def test_vector_store_delete_missing_collection_is_safe() -> None:
    store = VectorStore(persist_directory="data/chroma_test_missing")
    # Should not raise if called repeatedly for unknown collection.
    store.delete_collection("does_not_exist")
    store.delete_collection("does_not_exist")


def test_vector_store_uses_custom_persist_directory(tmp_path: Path) -> None:
    target = tmp_path / "custom_chroma"
    store = VectorStore(persist_directory=str(target))
    store.create_collection("book_custom")
    assert target.exists()
