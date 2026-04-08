from __future__ import annotations

import uuid
from pathlib import Path

from ebooklib import epub
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.db.database import Base, get_db


def _write_minimal_epub(path: Path, *, unique_token: str) -> None:
    """Valid EPUB with unique body text so file_hash differs per test run."""
    book = epub.EpubBook()
    book.set_identifier(f"id-{unique_token}")
    book.set_title("Sample EPUB")
    book.set_language("en")
    book.add_author("Author A")
    body = f"<p>Alpha rabbit smoke {unique_token}.</p>"
    c1 = epub.EpubHtml(title="One", file_name="chap_1.xhtml", content=f"<h1>One</h1>{body}")
    book.add_item(c1)
    book.toc = (c1,)
    book.spine = [c1]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)


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


def test_books_api_upload_list_get_delete(tmp_path: Path) -> None:
    client = TestClient(app)
    sample = tmp_path / "sample.epub"
    _write_minimal_epub(sample, unique_token=uuid.uuid4().hex)

    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("sample.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert response.status_code == 200
    payload = response.json()
    book_id = payload["id"]

    listed = client.get("/api/books")
    assert listed.status_code == 200
    assert any(item["id"] == book_id for item in listed.json())

    detail = client.get(f"/api/books/{book_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == book_id

    deleted = client.delete(f"/api/books/{book_id}")
    assert deleted.status_code == 200

    not_found = client.get(f"/api/books/{book_id}")
    assert not_found.status_code == 404


def test_books_api_upload_allows_chat_session_for_same_book(tmp_path: Path) -> None:
    """B01: uploaded book must exist in DB so chat session creation succeeds."""
    memory_db = _make_memory_session()

    def _override_db():
        yield memory_db

    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        sample = tmp_path / "chat.epub"
        _write_minimal_epub(sample, unique_token=uuid.uuid4().hex)
        with sample.open("rb") as f:
            up = client.post(
                "/api/books/upload",
                files={"file": ("chat.epub", f, "application/epub+zip")},
                data={"chunking_strategy": "paragraph"},
            )
        assert up.status_code == 200
        book_id = up.json()["id"]

        sess = client.post(
            "/api/chat/sessions",
            json={"book_id": book_id, "title": "Test session"},
        )
        assert sess.status_code == 200, sess.text
        assert sess.json()["book_id"] == book_id
    finally:
        app.dependency_overrides.clear()


def test_books_api_rejects_non_epub_upload(tmp_path: Path) -> None:
    client = TestClient(app)
    sample = tmp_path / "sample.txt"
    sample.write_text("dummy", encoding="utf-8")

    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("sample.txt", f, "text/plain")},
            data={"chunking_strategy": "paragraph"},
        )
    assert response.status_code == 400


def test_books_api_404_for_missing_book() -> None:
    client = TestClient(app)
    assert client.get("/api/books/999999").status_code == 404
    assert client.delete("/api/books/999999").status_code == 404


def test_books_api_rejects_unknown_chunking_strategy(tmp_path: Path) -> None:
    client = TestClient(app)
    sample = tmp_path / "sample.epub"
    _write_minimal_epub(sample, unique_token=uuid.uuid4().hex)
    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("sample.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "unsupported"},
        )
    assert response.status_code == 400


def test_books_api_rejects_duplicate_upload_same_bytes(tmp_path: Path) -> None:
    client = TestClient(app)
    sample = tmp_path / "dup.epub"
    _write_minimal_epub(sample, unique_token="fixed-dup-token")
    with sample.open("rb") as f:
        first = client.post(
            "/api/books/upload",
            files={"file": ("dup.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert first.status_code == 200
    with sample.open("rb") as f:
        second = client.post(
            "/api/books/upload",
            files={"file": ("dup.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert second.status_code == 409
