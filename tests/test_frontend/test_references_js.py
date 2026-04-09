"""Structural checks for the references panel (static/js/components/references.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REF_JS = ROOT / "static" / "js" / "components" / "references.js"


@pytest.fixture(scope="module")
def references_js() -> str:
    return REF_JS.read_text(encoding="utf-8")


def test_references_js_exists() -> None:
    assert REF_JS.is_file(), "static/js/components/references.js must exist"


def test_references_js_imports_get_book_chunks(references_js: str) -> None:
    assert "export " in references_js
    assert 'from "../api.js"' in references_js or "from '../api.js'" in references_js
    assert "getBookChunks" in references_js


def test_references_js_exports_init(references_js: str) -> None:
    assert "initReferences" in references_js


def test_references_js_dom_ids(references_js: str) -> None:
    assert "references-list" in references_js
    assert "clear-references" in references_js


def test_references_js_highlighting(references_js: str) -> None:
    lower = references_js.lower()
    assert "highlight" in lower or "mark" in lower


def test_references_js_clear_behavior(references_js: str) -> None:
    lower = references_js.lower()
    assert "clear" in lower


def test_references_js_chunk_display(references_js: str) -> None:
    lower = references_js.lower()
    assert "chunk" in lower and ("append" in lower or "render" in lower or "reference" in lower)


def test_references_js_append_passes_optional_scores(references_js: str) -> None:
    """B06: chat references show relevance scores from SSE (4 decimal places)."""
    assert "appendReferencedChunkIds" in references_js
    assert "Score:" in references_js
    assert "toFixed(4)" in references_js
