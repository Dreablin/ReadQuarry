from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings as app_config
from src.api.settings import get_settings
from src.core.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingService
from src.core.hybrid_search import HybridSearch
from src.core.llm_client import LLMClient
from src.core.search_engine import SearchEngine
from src.core.vector_store import VectorStore
from src.db.database import get_db
from src.models.book import Book
from src.models.chat import ChatMessage, ChatSession
from src.models.chunk import Chunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class CreateSessionBody(BaseModel):
    book_id: int = Field(gt=0)
    title: str | None = None


class SendMessageBody(BaseModel):
    content: str = Field(min_length=1)


def _sse_payload(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _build_context_chunks(db: Session, book_id: int, query: str, app_settings: dict[str, Any]) -> tuple[str, list[int]]:
    """Retrieve merged chunk context for RAG; skips embedding when the book has no chunks."""
    n_chunks = db.query(Chunk).filter(Chunk.book_id == book_id).count()
    if n_chunks == 0:
        return "", []

    semantic_k = int(app_settings.get("semantic_top_k", 5))
    exact_k = int(app_settings.get("exact_results", 5))
    final_n = int(app_settings.get("final_context_chunks", 7))

    embedder = EmbeddingService(
        model_name=str(app_settings.get("embedding_model") or DEFAULT_EMBEDDING_MODEL),
        device=str(app_settings.get("embedding_device") or "cpu"),
    )
    query_vector = embedder.embed_text(query)

    vs = VectorStore(persist_directory=str(app_config.data_dir / "chroma"))
    collection_name = f"book_{book_id}"
    semantic_results: list[dict[str, Any]] = []
    try:
        raw = vs.query(collection_name=collection_name, query_embedding=query_vector, n_results=semantic_k)
        ids = raw.get("ids", [[]])[0] if raw.get("ids") else []
        distances = raw.get("distances", [[]])[0] if raw.get("distances") else []
        for i, cid in enumerate(ids):
            if cid is None:
                continue
            try:
                chunk_id_int = int(cid)
            except (TypeError, ValueError):
                continue
            row = db.get(Chunk, chunk_id_int)
            if row is None or row.book_id != book_id:
                continue
            dist = float(distances[i]) if i < len(distances) else 0.0
            score = 1.0 / (1.0 + max(dist, 0.0))
            semantic_results.append({"chunk_id": str(chunk_id_int), "text": row.text, "score": score})
    except Exception:
        logger.exception("Semantic retrieval failed for book_id=%s", book_id)

    index_dir = str(app_config.data_dir / "tantivy_index" / f"book_{book_id}")
    engine = SearchEngine(index_dir=index_dir)
    exact_raw = engine.search(query, max_results=exact_k)
    exact_results: list[dict[str, Any]] = []
    for doc in exact_raw:
        try:
            cid = int(str(doc["chunk_id"]))
        except (TypeError, ValueError):
            continue
        row = db.get(Chunk, cid)
        if row is None or row.book_id != book_id:
            continue
        exact_results.append({"chunk_id": str(cid), "text": row.text, "score": 1.0})

    merged = HybridSearch().merge_results(semantic_results, exact_results, final_n=final_n)
    chunk_ids_ordered: list[int] = []
    lines: list[str] = []
    for i, row in enumerate(merged, start=1):
        try:
            cid = int(str(row["chunk_id"]))
        except (TypeError, ValueError):
            continue
        chunk_ids_ordered.append(cid)
        chunk_row = db.get(Chunk, cid)
        text = chunk_row.text if chunk_row else str(row.get("text", ""))
        lines.append(f"[{i}] (chunk {cid}) {text}")
    return "\n\n".join(lines), chunk_ids_ordered


def _system_prompt() -> str:
    return (
        "You are ReadQuarry, a book discussion assistant. Answer using only the excerpts below. "
        "When you use information from an excerpt, cite it with the matching bracket label like [1] or [2]. "
        "If the excerpts do not contain enough information, say so clearly."
    )


def _stream_chat(db: Session, session_id: int, user_text: str) -> Iterator[str]:
    session_row = db.get(ChatSession, session_id)
    if session_row is None:
        yield _sse_payload({"type": "error", "message": "Session not found"})
        return

    app_settings = get_settings()
    book_id = session_row.book_id

    user_msg = ChatMessage(session_id=session_id, role="user", content=user_text, referenced_chunks=None)
    db.add(user_msg)
    db.commit()

    context_text, ref_chunk_ids = _build_context_chunks(db, book_id, user_text, app_settings)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
    ]
    if context_text:
        user_block = f"Book excerpts:\n\n{context_text}\n\nQuestion:\n{user_text}"
    else:
        user_block = (
            "No indexed chunks were found for this book. Answer conservatively.\n\n"
            f"Question:\n{user_text}"
        )
    messages.append({"role": "user", "content": user_block})

    llm = LLMClient(dict(app_settings))
    assistant_parts: list[str] = []

    try:
        stream = llm.chat_completion(messages, stream=True)
        for chunk in stream:
            if not chunk.choices:
                logger.debug("LLM stream chunk without choices session_id=%s", session_id)
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                logger.debug("LLM stream chunk missing delta session_id=%s", session_id)
                continue
            piece = getattr(delta, "content", None) or ""
            logger.debug(
                "LLM stream delta session_id=%s piece_len=%d piece_preview=%r",
                session_id,
                len(piece),
                piece[:200] if isinstance(piece, str) else piece,
            )
            if not piece:
                continue
            assistant_parts.append(piece)
            # Stream only when there is visible text so far (avoids silent all-whitespace UIs).
            if "".join(assistant_parts).strip():
                yield _sse_payload({"type": "delta", "content": piece})
            else:
                logger.debug(
                    "LLM stream only whitespace accumulated so far session_id=%s",
                    session_id,
                )

        assistant_joined = "".join(assistant_parts)
        if not assistant_joined.strip():
            logger.warning(
                "LLM returned no visible text (empty or whitespace-only) session_id=%s",
                session_id,
            )
            placeholder = "[Empty block returned from LLM]"
            assistant_parts.clear()
            assistant_parts.append(placeholder)
            yield _sse_payload({"type": "delta", "content": placeholder})
    except Exception as exc:
        logger.exception("LLM streaming failed for session_id=%s", session_id)
        yield _sse_payload({"type": "error", "message": str(exc)})
        return

    assistant_text = "".join(assistant_parts)
    ref_json = json.dumps(ref_chunk_ids) if ref_chunk_ids else None
    assistant_row = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_text,
        referenced_chunks=ref_json,
    )
    db.add(assistant_row)
    db.commit()

    yield _sse_payload({"type": "done", "referenced_chunk_ids": ref_chunk_ids})


@router.post("/sessions")
def create_session(payload: CreateSessionBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    book = db.get(Book, payload.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    row = ChatSession(book_id=payload.book_id, title=payload.title)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "book_id": row.book_id,
        "title": row.title,
        "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
    }


@router.get("/sessions")
def list_sessions(book_id: int, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.book_id == book_id)
        .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "book_id": r.book_id,
            "title": r.title,
            "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
        }
        for r in rows
    ]


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: int, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    session_row = db.get(ChatSession, session_id)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for m in rows:
        refs: list[int] | None = None
        if m.referenced_chunks:
            try:
                refs = json.loads(m.referenced_chunks)
            except json.JSONDecodeError:
                refs = None
        out.append(
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "referenced_chunks": refs,
                "created_at": m.created_at.isoformat() if isinstance(m.created_at, datetime) else str(m.created_at),
            }
        )
    return out


@router.post("/sessions/{session_id}/message")
def send_message(session_id: int, payload: SendMessageBody, db: Session = Depends(get_db)) -> Any:
    if db.get(ChatSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        _stream_chat(db, session_id, payload.content),
        media_type="text/event-stream",
    )
