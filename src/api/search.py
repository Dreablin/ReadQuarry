from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.hybrid_search import HybridSearch
from src.core.search_engine import SearchEngine


router = APIRouter(prefix="/api/search", tags=["search"])


class SemanticSearchRequest(BaseModel):
    book_id: int
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, gt=0)


class ExactSearchRequest(BaseModel):
    book_id: int
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, gt=0)


class HybridSearchRequest(BaseModel):
    book_id: int
    query: str = Field(min_length=1)
    semantic_k: int = Field(default=5, gt=0)
    exact_k: int = Field(default=5, gt=0)
    final_n: int = Field(default=7, gt=0)


@router.post("/semantic")
def semantic_search(payload: SemanticSearchRequest) -> dict:
    # Placeholder semantic behavior for API contract wiring.
    results = [
        {
            "chunk_id": f"{payload.book_id}_sem_1",
            "text": f"Semantic match for '{payload.query}'",
            "score": 0.9,
        }
    ][: max(0, payload.top_k)]
    return {"results": results}


@router.post("/exact")
def exact_search(payload: ExactSearchRequest) -> dict:
    engine = SearchEngine(index_dir=f"data/tantivy_index/book_{payload.book_id}")
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
    return {"results": merged}
