"""B01-TEST: integration coverage for POST /api/books/upload Server-Sent Events."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from ebooklib import epub
from fastapi.testclient import TestClient

from main import app


def _write_minimal_epub(path: Path, *, unique_token: str) -> None:
    book = epub.EpubBook()
    book.set_identifier(f"id-{unique_token}")
    book.set_title("SSE Integration")
    book.set_language("en")
    body = f"<p>Integration token {unique_token}</p>"
    c1 = epub.EpubHtml(title="One", file_name="chap_1.xhtml", content=f"<h1>One</h1>{body}")
    book.add_item(c1)
    book.toc = (c1,)
    book.spine = [c1]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)


def _all_sse_events(response) -> list[dict]:
    out: list[dict] = []
    for block in response.text.split("\n\n"):
        for line in block.split("\n"):
            s = line.strip()
            if not s.startswith("data: "):
                continue
            try:
                out.append(json.loads(s[6:]))
            except json.JSONDecodeError:
                continue
    return out


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_b01_test_integration_upload_sse_stage_sequence_embedding_detail_and_done(
    client: TestClient, tmp_path: Path
) -> None:
    """B01-TEST: SSE includes parsing→chunking→embedding (with detail)→indexing→done+book."""
    sample = tmp_path / "integ_sse.epub"
    _write_minimal_epub(sample, unique_token=uuid.uuid4().hex)
    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("integ_sse.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers.get("content-type", "")
    events = _all_sse_events(response)
    assert events, "expected at least one SSE JSON payload"
    by_stage: dict[str, list[dict]] = {}
    for e in events:
        st = e.get("stage")
        if isinstance(st, str):
            by_stage.setdefault(st, []).append(e)
    assert "parsing" in by_stage
    assert "chunking" in by_stage
    assert "embedding" in by_stage
    emb_with_detail = [e for e in by_stage["embedding"] if isinstance(e.get("detail"), str)]
    assert any("Embedding" in str(e.get("detail")) for e in emb_with_detail), by_stage["embedding"]
    assert "indexing" in by_stage
    done = [e for e in events if e.get("stage") == "done"]
    assert len(done) == 1
    assert done[0].get("progress") == 100
    book = done[0].get("book")
    assert isinstance(book, dict) and book.get("id") is not None
    assert "error" not in by_stage


def test_b01_test_integration_upload_sse_error_stream_no_done_book(
    client: TestClient, tmp_path: Path
) -> None:
    """B01-TEST: corrupt EPUB yields SSE error event and HTTP 200; no finished book in stream."""
    bad = tmp_path / "corrupt.epub"
    bad.write_bytes(b"not-a-valid-epub-zip-content")
    listed_before = client.get("/api/books").json()
    n_before = len(listed_before)
    with bad.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("corrupt.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "paragraph"},
        )
    assert response.status_code == 200, response.text
    events = _all_sse_events(response)
    assert any(e.get("stage") == "error" for e in events), events
    assert not any(e.get("stage") == "done" for e in events)
    err = next(e for e in events if e.get("stage") == "error")
    assert isinstance(err.get("message"), str) and err["message"]
    listed_after = client.get("/api/books").json()
    assert len(listed_after) == n_before
