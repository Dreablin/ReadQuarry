from __future__ import annotations

from typing import Any


def filter_rows_by_min_score(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    """Drop rows whose ``score`` is strictly below ``threshold`` (higher-is-better)."""
    return [r for r in rows if float(r.get("score", 0.0)) >= threshold]


class HybridSearch:
    def merge_results(self, semantic_results: list[dict], exact_results: list[dict], final_n: int = 7) -> list[dict]:
        by_id: dict[str, dict] = {}
        scores: dict[str, float] = {}
        exact_hits: dict[str, int] = {}

        for item in semantic_results:
            chunk_id = str(item["chunk_id"])
            by_id[chunk_id] = {**item}
            scores[chunk_id] = scores.get(chunk_id, 0.0) + float(item.get("score", 0.0))

        for item in exact_results:
            chunk_id = str(item["chunk_id"])
            if chunk_id not in by_id:
                by_id[chunk_id] = {**item}
            scores[chunk_id] = scores.get(chunk_id, 0.0) + float(item.get("score", 0.0))
            exact_hits[chunk_id] = exact_hits.get(chunk_id, 0) + 1

        ranked = sorted(
            by_id.values(),
            key=lambda row: (
                scores.get(str(row["chunk_id"]), 0.0),
                exact_hits.get(str(row["chunk_id"]), 0),
            ),
            reverse=True,
        )
        out: list[dict] = []
        for row in ranked[: max(0, final_n)]:
            cid = str(row["chunk_id"])
            combined = float(scores.get(cid, 0.0))
            out.append({**row, "score": round(combined, 6)})
        return out
