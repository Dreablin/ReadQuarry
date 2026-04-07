"""Structural checks for the book list / selector component (static/js/components/book-list.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BOOK_LIST_JS = ROOT / "static" / "js" / "components" / "book-list.js"


@pytest.fixture(scope="module")
def book_list_js() -> str:
    return BOOK_LIST_JS.read_text(encoding="utf-8")


def test_book_list_js_exists() -> None:
    assert BOOK_LIST_JS.is_file(), "static/js/components/book-list.js must exist"


def test_book_list_js_es_module_imports_list_books(book_list_js: str) -> None:
    assert "export " in book_list_js
    assert 'from "../api.js"' in book_list_js or "from '../api.js'" in book_list_js
    assert "listBooks" in book_list_js


def test_book_list_js_exports_init(book_list_js: str) -> None:
    assert "initBookList" in book_list_js


def test_book_list_js_targets_book_select(book_list_js: str) -> None:
    assert "book-select" in book_list_js


def test_book_list_js_change_handler(book_list_js: str) -> None:
    assert "change" in book_list_js.lower()


def test_book_list_js_refresh_or_populate(book_list_js: str) -> None:
    lower = book_list_js.lower()
    assert "refresh" in lower or "populate" in lower or "option" in lower
