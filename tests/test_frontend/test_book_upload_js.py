"""Structural checks for the book upload component (static/js/components/book-upload.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BOOK_UPLOAD_JS = ROOT / "static" / "js" / "components" / "book-upload.js"


@pytest.fixture(scope="module")
def book_upload_js() -> str:
    return BOOK_UPLOAD_JS.read_text(encoding="utf-8")


def test_book_upload_js_exists() -> None:
    assert BOOK_UPLOAD_JS.is_file(), "static/js/components/book-upload.js must exist"


def test_book_upload_js_es_module_imports_api(book_upload_js: str) -> None:
    assert "export " in book_upload_js
    assert 'from "../api.js"' in book_upload_js or "from '../api.js'" in book_upload_js
    assert "uploadBook" in book_upload_js


def test_book_upload_js_init_export(book_upload_js: str) -> None:
    assert "initBookUpload" in book_upload_js


def test_book_upload_js_drag_drop_hooks(book_upload_js: str) -> None:
    lower = book_upload_js.lower()
    assert "dragover" in lower
    assert "drop" in lower
    assert "preventdefault" in lower.replace(" ", "")


def test_book_upload_js_chunking_strategy(book_upload_js: str) -> None:
    assert "chunking" in book_upload_js.lower()


def test_book_upload_js_progress_bar(book_upload_js: str) -> None:
    assert "progress" in book_upload_js.lower()
    assert "upload-progress" in book_upload_js or "aria-valuenow" in book_upload_js


def test_book_upload_js_dialog_and_file_input(book_upload_js: str) -> None:
    assert "upload-dialog" in book_upload_js
    assert "upload-file" in book_upload_js
