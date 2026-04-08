from pathlib import Path

from src.core.search_engine import SearchEngine


def test_search_engine_index_and_search(tmp_path: Path) -> None:
    engine = SearchEngine(index_dir=str(tmp_path / "t1"))
    engine.index_documents(
        [
            {"chunk_id": "1", "text": "Alice meets the rabbit", "chapter": "1", "chunk_index": 0},
            {"chunk_id": "2", "text": "The rabbit is late", "chapter": "1", "chunk_index": 1},
        ]
    )
    results = engine.search("rabbit")
    assert len(results) >= 1
    assert any("rabbit" in r["text"].lower() for r in results)


def test_search_engine_case_insensitive_search(tmp_path: Path) -> None:
    engine = SearchEngine(index_dir=str(tmp_path / "t2"))
    engine.index_documents([{"chunk_id": "1", "text": "Wonderland", "chapter": "1", "chunk_index": 0}])
    assert len(engine.search("wonderland")) >= 1
    assert len(engine.search("WONDERLAND")) >= 1


def test_search_engine_phrase_search(tmp_path: Path) -> None:
    engine = SearchEngine(index_dir=str(tmp_path / "phrase"))
    engine.index_documents(
        [
            {"chunk_id": "1", "text": "Alice meets white rabbit in wonderland", "chapter": "1", "chunk_index": 0},
            {"chunk_id": "2", "text": "Rabbit appears alone", "chapter": "1", "chunk_index": 1},
        ]
    )
    results = engine.search('"white rabbit"')
    assert len(results) == 1
    assert results[0]["chunk_id"] == "1"


def test_search_engine_word_search_returns_ranked_subset(tmp_path: Path) -> None:
    engine = SearchEngine(index_dir=str(tmp_path / "rank"))
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


def test_search_engine_delete_index(tmp_path: Path) -> None:
    engine = SearchEngine(index_dir=str(tmp_path / "t3"))
    engine.index_documents([{"chunk_id": "1", "text": "to be removed", "chapter": "1", "chunk_index": 0}])
    assert len(engine.search("removed")) == 1
    engine.delete_index()
    assert engine.search("removed") == []


def test_search_engine_persists_across_instances(tmp_path: Path) -> None:
    d = str(tmp_path / "persist")
    e1 = SearchEngine(index_dir=d)
    e1.index_documents([{"chunk_id": "a", "text": "persistent fox tale", "chapter": "x", "chunk_index": 0}])
    e2 = SearchEngine(index_dir=d)
    assert len(e2.search("fox")) == 1
    assert e2.search("fox")[0]["chunk_id"] == "a"


def test_search_engine_uses_custom_persist_directory(tmp_path: Path) -> None:
    custom = tmp_path / "custom_tantivy"
    engine = SearchEngine(index_dir=str(custom))
    engine.index_documents([{"chunk_id": "1", "text": "custom path doc", "chapter": "1", "chunk_index": 0}])
    assert (custom / "documents.json").is_file()
    assert len(engine.search("custom")) == 1
