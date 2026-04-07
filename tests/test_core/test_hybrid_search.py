from src.core.hybrid_search import HybridSearch


def test_hybrid_search_merges_and_deduplicates() -> None:
    hybrid = HybridSearch()
    semantic = [
        {"chunk_id": "1", "text": "alpha", "score": 0.9},
        {"chunk_id": "2", "text": "beta", "score": 0.7},
    ]
    exact = [
        {"chunk_id": "2", "text": "beta", "score": 1.0},
        {"chunk_id": "3", "text": "gamma", "score": 0.8},
    ]
    merged = hybrid.merge_results(semantic, exact, final_n=5)
    ids = [m["chunk_id"] for m in merged]
    assert ids.count("2") == 1
    assert set(ids) == {"1", "2", "3"}


def test_hybrid_search_ranking_prefers_combined_hits() -> None:
    hybrid = HybridSearch()
    semantic = [
        {"chunk_id": "1", "text": "alpha", "score": 0.4},
        {"chunk_id": "2", "text": "beta", "score": 0.3},
    ]
    exact = [
        {"chunk_id": "1", "text": "alpha", "score": 0.9},
        {"chunk_id": "3", "text": "gamma", "score": 1.0},
    ]
    merged = hybrid.merge_results(semantic, exact, final_n=3)
    assert merged[0]["chunk_id"] == "1"


def test_hybrid_search_limits_to_final_n() -> None:
    hybrid = HybridSearch()
    semantic = [{"chunk_id": str(i), "text": f"t{i}", "score": 0.1} for i in range(10)]
    exact = []
    merged = hybrid.merge_results(semantic, exact, final_n=4)
    assert len(merged) == 4


def test_hybrid_search_handles_empty_inputs() -> None:
    hybrid = HybridSearch()
    assert hybrid.merge_results([], [], final_n=5) == []


def test_hybrid_search_prefers_exact_on_tie_with_semantic_only() -> None:
    hybrid = HybridSearch()
    semantic = [{"chunk_id": "1", "text": "alpha", "score": 0.5}]
    exact = [{"chunk_id": "2", "text": "beta", "score": 0.5}]
    merged = hybrid.merge_results(semantic, exact, final_n=2)
    assert merged[0]["chunk_id"] == "2"


def test_hybrid_search_aggregates_multiple_exact_hits_for_same_chunk() -> None:
    hybrid = HybridSearch()
    semantic = []
    exact = [
        {"chunk_id": "5", "text": "x", "score": 0.2},
        {"chunk_id": "5", "text": "x", "score": 0.4},
        {"chunk_id": "6", "text": "y", "score": 0.5},
    ]
    merged = hybrid.merge_results(semantic, exact, final_n=3)
    assert merged[0]["chunk_id"] == "5"
