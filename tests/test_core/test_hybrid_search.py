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
