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


def test_search_engine_phrase_search() -> None:
    engine = SearchEngine(index_dir="data/tantivy_test_phrase")
    engine.index_documents(
        [
            {"chunk_id": "1", "text": "Alice meets white rabbit in wonderland", "chapter": "1", "chunk_index": 0},
            {"chunk_id": "2", "text": "Rabbit appears alone", "chapter": "1", "chunk_index": 1},
        ]
    )
    results = engine.search('"white rabbit"')
    assert len(results) == 1
    assert results[0]["chunk_id"] == "1"


def test_search_engine_word_search_returns_ranked_subset() -> None:
    engine = SearchEngine(index_dir="data/tantivy_test_rank")
    engine.index_documents(
        [
            {"chunk_id": "1", "text": "rabbit rabbit rabbit", "chapter": "1", "chunk_index": 0},
            {"chunk_id": "2", "text": "rabbit", "chapter": "1", "chunk_index": 1},
            {"chunk_id": "3", "text": "rabbit hole", "chapter": "1", "chunk_index": 2},
        ]
    )
    results = engine.search("rabbit", max_results=2)
    assert len(results) == 2
    assert results[0]["chunk_id"] == "1"


def test_search_engine_delete_index() -> None:
    engine = SearchEngine(index_dir="data/tantivy_test_3")
    engine.index_documents([{"chunk_id": "1", "text": "to be removed", "chapter": "1", "chunk_index": 0}])
    assert len(engine.search("removed")) == 1
    engine.delete_index()
    assert engine.search("removed") == []
