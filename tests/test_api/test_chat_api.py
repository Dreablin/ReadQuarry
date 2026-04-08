from __future__ import annotations

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
    import src.models  # noqa: F401  # register models on Base.metadata before create_all

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
        title="Test",
        author=None,
        file_name="t.epub",
        file_hash="chat-test-hash",
        chunking_strategy="paragraph",
        total_paragraphs=0,
        total_chunks=0,
    )
    session.add(book)
    session.commit()
    session.refresh(book)
    return book.id


def test_chat_create_session_returns_404_when_book_missing(client_with_db: TestClient, memory_db: Session) -> None:
    r = client_with_db.post("/api/chat/sessions", json={"book_id": 99999})
    assert r.status_code == 404


def test_chat_create_session_and_list(client_with_db: TestClient, memory_db: Session) -> None:
    bid = _insert_book(memory_db)
    r = client_with_db.post("/api/chat/sessions", json={"book_id": bid, "title": "Discuss"})
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert body["book_id"] == bid
    assert body["title"] == "Discuss"

    listed = client_with_db.get("/api/chat/sessions", params={"book_id": bid})
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]


def test_chat_messages_empty_then_post_streams_sse(client_with_db: TestClient, memory_db: Session) -> None:
    bid = _insert_book(memory_db)
    sid = client_with_db.post("/api/chat/sessions", json={"book_id": bid}).json()["id"]

    hist = client_with_db.get(f"/api/chat/sessions/{sid}/messages")
    assert hist.status_code == 200
    assert hist.json() == []

    def _fake_stream() -> object:
        for text in ("Hel", "lo"):
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=text))]
            yield chunk
        end = MagicMock()
        end.choices = [MagicMock(delta=MagicMock(content=None))]
        yield end

    with patch("src.api.chat.LLMClient") as mock_llm_cls:
        mock_llm_cls.return_value.chat_completion.return_value = _fake_stream()
        r = client_with_db.post(
            f"/api/chat/sessions/{sid}/message",
            json={"content": "Hi there"},
        )

    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/event-stream")
    body = r.text
    assert "delta" in body
    assert "done" in body

    hist2 = client_with_db.get(f"/api/chat/sessions/{sid}/messages")
    assert hist2.status_code == 200
    msgs = hist2.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hi there"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "Hello"


def test_chat_message_404_bad_session(client_with_db: TestClient, memory_db: Session) -> None:
    _insert_book(memory_db)
    r = client_with_db.post("/api/chat/sessions/99999/message", json={"content": "x"})
    assert r.status_code == 404


def test_chat_list_sessions_requires_book_id(client_with_db: TestClient, memory_db: Session) -> None:
    r = client_with_db.get("/api/chat/sessions")
    assert r.status_code == 422


def test_chat_get_messages_404_unknown_session(client_with_db: TestClient, memory_db: Session) -> None:
    _insert_book(memory_db)
    r = client_with_db.get("/api/chat/sessions/99999/messages")
    assert r.status_code == 404


def test_chat_post_message_rejects_empty_content(client_with_db: TestClient, memory_db: Session) -> None:
    bid = _insert_book(memory_db)
    sid = client_with_db.post("/api/chat/sessions", json={"book_id": bid}).json()["id"]
    r = client_with_db.post(f"/api/chat/sessions/{sid}/message", json={"content": ""})
    assert r.status_code == 422


def test_chat_create_session_rejects_non_positive_book_id(client_with_db: TestClient, memory_db: Session) -> None:
    r = client_with_db.post("/api/chat/sessions", json={"book_id": 0})
    assert r.status_code == 422


def test_chat_sessions_list_newest_first(client_with_db: TestClient, memory_db: Session) -> None:
    bid = _insert_book(memory_db)
    first = client_with_db.post("/api/chat/sessions", json={"book_id": bid, "title": "Older"}).json()
    second = client_with_db.post("/api/chat/sessions", json={"book_id": bid, "title": "Newer"}).json()
    listed = client_with_db.get("/api/chat/sessions", params={"book_id": bid}).json()
    assert len(listed) == 2
    assert listed[0]["id"] == second["id"]
    assert listed[0]["title"] == "Newer"
    assert listed[1]["id"] == first["id"]


def test_chat_messages_history_order_after_two_turns(client_with_db: TestClient, memory_db: Session) -> None:
    bid = _insert_book(memory_db)
    sid = client_with_db.post("/api/chat/sessions", json={"book_id": bid}).json()["id"]

    def _stream_once(text: str) -> object:
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content=text))]
        yield chunk

    with patch("src.api.chat.LLMClient") as mock_llm_cls:
        mock_llm_cls.return_value.chat_completion.return_value = _stream_once("A")
        client_with_db.post(f"/api/chat/sessions/{sid}/message", json={"content": "one"})
        mock_llm_cls.return_value.chat_completion.return_value = _stream_once("B")
        client_with_db.post(f"/api/chat/sessions/{sid}/message", json={"content": "two"})

    msgs = client_with_db.get(f"/api/chat/sessions/{sid}/messages").json()
    assert len(msgs) == 4
    roles = [m["role"] for m in msgs]
    contents = [m["content"] for m in msgs]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert contents == ["one", "A", "two", "B"]


def test_chat_sse_stream_empty_llm_yields_placeholder_delta(client_with_db: TestClient, memory_db: Session) -> None:
    """B04: empty delta stream must still emit a visible placeholder for the UI."""
    bid = _insert_book(memory_db)
    sid = client_with_db.post("/api/chat/sessions", json={"book_id": bid}).json()["id"]

    def _only_empty_deltas() -> object:
        for _ in range(3):
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=""))]
            yield chunk

    with patch("src.api.chat.LLMClient") as mock_llm_cls:
        mock_llm_cls.return_value.chat_completion.return_value = _only_empty_deltas()
        r = client_with_db.post(
            f"/api/chat/sessions/{sid}/message",
            json={"content": "Hi"},
        )

    assert r.status_code == 200
    assert "[Empty block returned from LLM]" in r.text
    hist = client_with_db.get(f"/api/chat/sessions/{sid}/messages").json()
    assert len(hist) == 2
    assert hist[1]["role"] == "assistant"
    assert "[Empty block returned from LLM]" in hist[1]["content"]


def test_chat_sse_stream_includes_error_when_llm_raises(client_with_db: TestClient, memory_db: Session) -> None:
    bid = _insert_book(memory_db)
    sid = client_with_db.post("/api/chat/sessions", json={"book_id": bid}).json()["id"]

    with patch("src.api.chat.LLMClient") as mock_llm_cls:
        mock_llm_cls.return_value.chat_completion.side_effect = RuntimeError("provider down")
        r = client_with_db.post(
            f"/api/chat/sessions/{sid}/message",
            json={"content": "Hi"},
        )

    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/event-stream")
    assert "error" in r.text
    assert "provider down" in r.text
    assert "done" not in r.text
    hist = client_with_db.get(f"/api/chat/sessions/{sid}/messages").json()
    assert len(hist) == 1
    assert hist[0]["role"] == "user"
