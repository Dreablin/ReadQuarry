"""
Automated smoke flow for T41 — mirrors manual checklist: SPA, settings, EPUB upload,
search, and chat (SQLite book + mocked LLM).

Manual browser verification remains recommended for UI affordances.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.db.database import Base, get_db
from src.models.book import Book


def _make_memory_session() -> Session:
    import src.models  # noqa: F401  # register models

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


@pytest.fixture
def memory_db() -> Session:
    return _make_memory_session()


@pytest.fixture
def client_with_db(memory_db: Session) -> TestClient:
    def _override_db():
        yield memory_db

    app.dependency_overrides[get_db] = _override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _insert_book(session: Session) -> int:
    book = Book(
        title="E2E Smoke",
        author=None,
        file_name="smoke.epub",
        file_hash="e2e-smoke-hash",
        chunking_strategy="paragraph",
        total_paragraphs=0,
        total_chunks=0,
    )
    session.add(book)
    session.commit()
    session.refresh(book)
    return book.id


def test_readquarry_end_to_end_smoke(
    tmp_path: Path,
    client_with_db: TestClient,
    memory_db: Session,
) -> None:
    """Exercise static SPA, settings, upload, hybrid search, and chat in one flow."""
    client = client_with_db

    root = client.get("/")
    assert root.status_code == 200
    assert "ReadQuarry" in root.text

    assert client.get("/health").json() == {"status": "ok"}

    settings = client.get("/api/settings")
    assert settings.status_code == 200
    assert settings.json()["llm_mode"] in {"ollama", "cloud"}

    assert client.post("/api/settings/test-llm").status_code == 200

    epub = tmp_path / "smoke.epub"
    epub.write_bytes(b"dummy epub bytes for smoke")
    with epub.open("rb") as f:
        up = client.post(
            "/api/books/upload",
            files={"file": ("smoke.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert up.status_code == 200
    book_id = up.json()["id"]

    listed = client.get("/api/books")
    assert listed.status_code == 200
    assert any(b["id"] == book_id for b in listed.json())

    search = client.post(
        "/api/search/hybrid",
        json={
            "book_id": book_id,
            "query": "smoke",
            "semantic_k": 2,
            "exact_k": 2,
            "final_n": 3,
        },
    )
    assert search.status_code == 200
    assert "results" in search.json()

    bid = _insert_book(memory_db)
    sid = client.post(
        "/api/chat/sessions",
        json={"book_id": bid, "title": "Smoke session"},
    ).json()["id"]

    def _fake_stream() -> object:
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content="Hi"))]
        yield chunk
        end = MagicMock()
        end.choices = [MagicMock(delta=MagicMock(content=None))]
        yield end

    with patch("src.api.chat.LLMClient") as mock_llm_cls:
        mock_llm_cls.return_value.chat_completion.return_value = _fake_stream()
        msg = client.post(
            f"/api/chat/sessions/{sid}/message",
            json={"content": "Hello?"},
        )

    assert msg.status_code == 200
    assert msg.headers.get("content-type", "").startswith("text/event-stream")
    assert "done" in msg.text

    messages = client.get(f"/api/chat/sessions/{sid}/messages").json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
