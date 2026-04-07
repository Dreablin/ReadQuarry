from src.core.search_engine import SearchEngine


def test_search_engine_index_and_search() -> None:
    engine = SearchEngine(index_dir="data/tantivy_test_1")
    engine.index_documents(
        [
            {"chunk_id": "1", "text": "Alice meets the rabbit", "chapter": "1", "chunk_index": 0},
            {"chunk_id": "2", "text": "The rabbit is late", "chapter": "1", "chunk_index": 1},
        ]
    )
    results = engine.search("rabbit")
    assert len(results) >= 1
    assert any("rabbit" in r["text"].lower() for r in results)


def test_search_engine_case_insensitive_search() -> None:
    engine = SearchEngine(index_dir="data/tantivy_test_2")
    engine.index_documents([{"chunk_id": "1", "text": "Wonderland", "chapter": "1", "chunk_index": 0}])
    assert len(engine.search("wonderland")) >= 1
    assert len(engine.search("WONDERLAND")) >= 1


def test_search_engine_delete_index() -> None:
    engine = SearchEngine(index_dir="data/tantivy_test_3")
    engine.index_documents([{"chunk_id": "1", "text": "to be removed", "chapter": "1", "chunk_index": 0}])
    assert len(engine.search("removed")) == 1
    engine.delete_index()
    assert engine.search("removed") == []
