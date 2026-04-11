from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from ebooklib import epub
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.api import books as books_module
from src.db.database import Base, get_db


def _parse_upload_sse(response) -> tuple[list[dict], dict | None]:
    """Parse ``POST /api/books/upload`` SSE body into events and optional ``book`` from ``done``."""
    assert response.status_code == 200, response.text
    ct = response.headers.get("content-type", "")
    assert "text/event-stream" in ct, ct
    events: list[dict] = []
    done_book: dict | None = None
    for block in response.text.split("\n\n"):
        for line in block.split("\n"):
            s = line.strip()
            if not s.startswith("data: "):
                continue
            obj = json.loads(s[6:])
            events.append(obj)
            if obj.get("stage") == "done":
                done_book = obj.get("book")
            if obj.get("stage") == "error":
                raise AssertionError(f"SSE error event: {obj}")
    return events, done_book


def _upload_done_book(response) -> dict:
    """Require a successful upload stream and return the ``book`` object from the final event."""
    _events, book = _parse_upload_sse(response)
    assert book is not None and isinstance(book, dict)
    return book


def _write_minimal_epub(path: Path, *, unique_token: str, word_count: int | None = None) -> None:
    """Valid EPUB with unique body text so file_hash differs per test run."""
    book = epub.EpubBook()
    book.set_identifier(f"id-{unique_token}")
    book.set_title("Sample EPUB")
    book.set_language("en")
    book.add_author("Author A")
    if word_count is not None and word_count > 0:
        words = " ".join(f"w{i}x{unique_token[:4]}" for i in range(word_count))
        body = f"<p>{words}</p>"
    else:
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


def test_books_upload_logs_save_path_and_book_id(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """B11: upload endpoint logs destination path and book id for the log viewer."""
    caplog.set_level(logging.INFO, logger="src.api.books")
    client = TestClient(app)
    sample = tmp_path / "logged.epub"
    _write_minimal_epub(sample, unique_token=uuid.uuid4().hex)
    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("logged.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert response.status_code == 200
    book_id = _upload_done_book(response)["id"]
    books_logs = [r for r in caplog.records if r.name == "src.api.books"]
    text = " ".join(r.getMessage() for r in books_logs)
    assert str(book_id) in text
    assert "uploads" in text.replace("\\", "/").lower() or "Saving" in text


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
    payload = _upload_done_book(response)
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
        book_id = _upload_done_book(up)["id"]

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
    _upload_done_book(first)  # consume SSE stream
    with sample.open("rb") as f:
        second = client.post(
            "/api/books/upload",
            files={"file": ("dup.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert second.status_code == 409


def test_books_api_duplicate_upload_logs_warning(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """B13: duplicate upload path logs a warning with hash and filename for the log viewer."""
    caplog.set_level(logging.WARNING, logger="src.api.books")
    client = TestClient(app)
    sample = tmp_path / "dup_warn.epub"
    _write_minimal_epub(sample, unique_token="b13-dup-warn-token")
    with sample.open("rb") as f:
        first = client.post(
            "/api/books/upload",
            files={"file": ("dup_warn.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert first.status_code == 200
    _upload_done_book(first)
    with sample.open("rb") as f:
        r = client.post(
            "/api/books/upload",
            files={"file": ("dup_warn.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert r.status_code == 409
    warns = [rec for rec in caplog.records if rec.name == "src.api.books" and rec.levelno == logging.WARNING]
    assert warns, "expected WARNING from books API on duplicate"
    joined = " ".join(rec.getMessage() for rec in warns)
    assert "Duplicate book upload rejected" in joined
    assert "dup_warn.epub" in joined


def test_books_api_delete_all_clears_books_and_returns_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B16: DELETE /api/books removes every book, files, indices; returns deleted_count."""
    memory_db = _make_memory_session()

    def _override_db():
        yield memory_db

    monkeypatch.setattr(books_module, "settings", SimpleNamespace(data_dir=tmp_path))
    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        for name, token in (("a.epub", "clear-a"), ("b.epub", "clear-b")):
            p = tmp_path / name
            _write_minimal_epub(p, unique_token=token)
            with p.open("rb") as f:
                r = client.post(
                    "/api/books/upload",
                    files={"file": (name, f, "application/epub+zip")},
                    data={"chunking_strategy": "paragraph"},
                )
            assert r.status_code == 200, r.text

        listed = client.get("/api/books")
        assert listed.status_code == 200
        assert len(listed.json()) == 2

        cleared = client.delete("/api/books")
        assert cleared.status_code == 200
        data = cleared.json()
        assert data["status"] == "cleared"
        assert data["deleted_count"] == 2

        empty = client.get("/api/books")
        assert empty.status_code == 200
        assert empty.json() == []
    finally:
        app.dependency_overrides.clear()


def test_books_api_delete_all_logs_info(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B16: clear-all logs deleted count at INFO."""
    caplog.set_level(logging.INFO, logger="src.api.books")
    memory_db = _make_memory_session()

    def _override_db():
        yield memory_db

    monkeypatch.setattr(books_module, "settings", SimpleNamespace(data_dir=tmp_path))
    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        p = tmp_path / "one.epub"
        _write_minimal_epub(p, unique_token="clear-log")
        with p.open("rb") as f:
            assert (
                client.post(
                    "/api/books/upload",
                    files={"file": ("one.epub", f, "application/epub+zip")},
                    data={"chunking_strategy": "paragraph"},
                ).status_code
                == 200
            )
        client.delete("/api/books")
        infos = [r for r in caplog.records if r.name == "src.api.books" and "Cleared all books" in r.getMessage()]
        assert infos
        assert "count=1" in infos[-1].getMessage()
    finally:
        app.dependency_overrides.clear()


def test_books_api_upload_b06_fixed_size_chunk_size_affects_chunk_count(tmp_path: Path) -> None:
    """B06: smaller chunk_size yields more chunks for the same long body."""
    client = TestClient(app)
    tok_a = uuid.uuid4().hex
    tok_b = uuid.uuid4().hex
    pa = tmp_path / f"b06a_{tok_a}.epub"
    pb = tmp_path / f"b06b_{tok_b}.epub"
    _write_minimal_epub(pa, unique_token=tok_a, word_count=120)
    _write_minimal_epub(pb, unique_token=tok_b, word_count=120)
    with pa.open("rb") as fa:
        ra = client.post(
            "/api/books/upload",
            files={"file": ("a.epub", fa, "application/epub+zip")},
            data={
                "chunking_strategy": "fixed-size",
                "chunk_size": "50",
                "overlap_ratio": "0.1",
            },
        )
    with pb.open("rb") as fb:
        rb = client.post(
            "/api/books/upload",
            files={"file": ("b.epub", fb, "application/epub+zip")},
            data={
                "chunking_strategy": "fixed-size",
                "chunk_size": "80",
                "overlap_ratio": "0.1",
            },
        )
    assert ra.status_code == 200, ra.text
    assert rb.status_code == 200, rb.text
    book_a = _upload_done_book(ra)
    book_b = _upload_done_book(rb)
    # Compare ingestion counts from the upload stream, not GET /chunks (persistent DB can
    # accumulate duplicate chunk rows across test runs for the same book id).
    assert book_a["total_chunks"] > book_b["total_chunks"]


def test_books_api_upload_b01_sse_streams_progress_then_done(tmp_path: Path) -> None:
    """B01: upload returns SSE with non-decreasing progress and a terminal done book payload."""
    client = TestClient(app)
    sample = tmp_path / "sse.epub"
    _write_minimal_epub(sample, unique_token=uuid.uuid4().hex)
    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("sse.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    events, book = _parse_upload_sse(response)
    assert book is not None
    assert book.get("id") is not None
    stages = [e for e in events if e.get("stage") not in ("done", "error")]
    progresses = [int(e["progress"]) for e in stages if "progress" in e]
    assert progresses == sorted(progresses), progresses
    assert progresses[0] >= 10
    assert progresses[-1] >= 40
    done_events = [e for e in events if e.get("stage") == "done"]
    assert len(done_events) == 1
    assert done_events[0].get("progress") == 100
    assert "parsing" in {e.get("stage") for e in stages}
    assert "chunking" in {e.get("stage") for e in stages}
