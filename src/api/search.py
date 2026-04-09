from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import settings
from src.api.settings import get_settings
from src.core.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingService
from src.core.hybrid_search import HybridSearch, filter_rows_by_min_score
from src.core.search_engine import SearchEngine
from src.core.vector_store import VectorStore


router = APIRouter(prefix="/api/search", tags=["search"])


class SemanticSearchRequest(BaseModel):
    book_id: int
    query: str = Field(min_length=1)
    top_k: int = Field(default=15, gt=0, le=50)


class ExactSearchRequest(BaseModel):
    book_id: int
    query: str = Field(min_length=1)
    max_results: int = Field(default=15, gt=0, le=50)


class HybridSearchRequest(BaseModel):
    book_id: int
    query: str = Field(min_length=1)
    semantic_k: int = Field(default=15, gt=0, le=50)
    exact_k: int = Field(default=15, gt=0, le=50)
    final_n: int = Field(default=20, gt=0, le=50)


def _chroma_query_to_results(raw: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
    """Map Chroma query output to API result rows with higher-is-better score."""
    ids_outer = raw.get("ids") or []
    if not ids_outer:
        return []
    ids = ids_outer[0] or []
    documents_outer = raw.get("documents") or []
    documents = (documents_outer[0] if documents_outer else None) or []
    distances_outer = raw.get("distances") or []
    distances = (distances_outer[0] if distances_outer else None) or []
    results: list[dict[str, Any]] = []
    for i, chunk_id in enumerate(ids[:top_k]):
        text = str(documents[i]) if i < len(documents) else ""
        dist = float(distances[i]) if i < len(distances) else 0.0
        score = 1.0 / (1.0 + max(dist, 0.0))
        results.append(
            {
                "chunk_id": str(chunk_id),
                "text": text,
                "score": round(score, 6),
            }
        )
    return results


def _score_threshold_from_settings(app_settings: dict[str, Any]) -> float:
    raw = app_settings.get("search_score_threshold", 0.6)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.6


@router.post("/semantic")
def semantic_search(payload: SemanticSearchRequest) -> dict:
    app_settings = get_settings()
    embedding_service = EmbeddingService(
        model_name=str(app_settings.get("embedding_model") or DEFAULT_EMBEDDING_MODEL),
        device=str(app_settings.get("embedding_device") or "cpu"),
    )
    query_embedding = embedding_service.embed_text(payload.query)
    store = VectorStore(persist_directory=str(settings.data_dir / "chroma"))
    collection_name = f"book_{payload.book_id}"
    raw = store.query(collection_name, query_embedding, n_results=payload.top_k)
    results = _chroma_query_to_results(raw, payload.top_k)
    threshold = _score_threshold_from_settings(app_settings)
    results = filter_rows_by_min_score(results, threshold)
    return {"results": results}


@router.post("/exact")
def exact_search(payload: ExactSearchRequest) -> dict:
    engine = SearchEngine(
        index_dir=str(settings.data_dir / "tantivy_index" / f"book_{payload.book_id}")
    )
    results = engine.search(payload.query, max_results=payload.max_results)
    return {"results": results}


@router.post("/hybrid")
def hybrid_search(payload: HybridSearchRequest) -> dict:
    semantic = semantic_search(
        SemanticSearchRequest(book_id=payload.book_id, query=payload.query, top_k=payload.semantic_k)
    )["results"]
    exact = exact_search(
        ExactSearchRequest(book_id=payload.book_id, query=payload.query, max_results=payload.exact_k)
    )["results"]
    merged = HybridSearch().merge_results(semantic, exact, final_n=payload.final_n)
    threshold = _score_threshold_from_settings(get_settings())
    merged = filter_rows_by_min_score(merged, threshold)
    return {"results": merged}
