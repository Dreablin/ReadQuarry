from pathlib import Path

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_books_api_upload_list_get_delete(tmp_path: Path) -> None:
    sample = tmp_path / "sample.epub"
    sample.write_text("dummy", encoding="utf-8")

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


def test_books_api_rejects_non_epub_upload(tmp_path: Path) -> None:
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
    assert client.get("/api/books/999999").status_code == 404
    assert client.delete("/api/books/999999").status_code == 404


def test_books_api_rejects_unknown_chunking_strategy(tmp_path: Path) -> None:
    sample = tmp_path / "sample.epub"
    sample.write_text("dummy", encoding="utf-8")
    with sample.open("rb") as f:
        response = client.post(
            "/api/books/upload",
            files={"file": ("sample.epub", f, "application/epub+zip")},
            data={"chunking_strategy": "unsupported"},
        )
    assert response.status_code == 400
