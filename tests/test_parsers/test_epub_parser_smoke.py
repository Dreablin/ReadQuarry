from pathlib import Path

from ebooklib import epub

from src.parsers.base import ParsedBook
from src.parsers.epub_parser import EpubParser


def test_epub_parser_reports_supported_extension() -> None:
    parser = EpubParser()
    assert ".epub" in parser.supported_extensions()


def test_epub_parser_can_parse_by_extension() -> None:
    parser = EpubParser()
    assert parser.can_parse("book.epub") is True
    assert parser.can_parse("book.txt") is False


def test_epub_parser_exposes_clean_html_helper() -> None:
    parser = EpubParser()
    cleaned = parser.clean_html("<h1>Title</h1><p>Hello <b>world</b></p>")
    assert "Title" in cleaned
    assert "Hello world" in cleaned
    assert "<h1>" not in cleaned


def test_epub_parser_clean_html_preserves_paragraph_breaks_for_chunking() -> None:
    """B06: block boundaries must survive as blank-line gaps for ParagraphChunking."""
    parser = EpubParser()
    cleaned = parser.clean_html("<p>First paragraph.</p><p>Second paragraph.</p>")
    assert "First paragraph." in cleaned
    assert "Second paragraph." in cleaned
    assert "\n\n" in cleaned


def test_epub_parser_clean_html_b04_includes_leaf_div_paragraphs_when_p_exists() -> None:
    """B04: must not return early on first <p> and drop sibling <div> body text."""
    parser = EpubParser()
    html = (
        '<p>Footer note.</p>'
        '<div class="para">First div block.</div>'
        '<div class="para">Second div block.</div>'
    )
    cleaned = parser.clean_html(html)
    parts = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    assert len(parts) == 3
    assert "Footer note." in cleaned
    assert "First div block." in cleaned
    assert "Second div block." in cleaned


def test_epub_parser_clean_html_b04_blockquote_inner_p_not_duplicated() -> None:
    """B04: <blockquote><p>…</p></blockquote> yields one block, not two."""
    parser = EpubParser()
    cleaned = parser.clean_html("<blockquote><p>Single quoted line.</p></blockquote>")
    assert cleaned.count("Single quoted line.") == 1
    parts = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    assert len(parts) == 1


def test_epub_parser_clean_html_b04_blockquote_plain_text() -> None:
    """B04: blockquote without inner block tags still extracts."""
    parser = EpubParser()
    cleaned = parser.clean_html("<blockquote>Bare quote.</blockquote>")
    assert "Bare quote." in cleaned


def test_epub_parser_clean_html_b04_expanded_block_tags() -> None:
    """B04: blockquote, pre, td, figcaption appear as separate blocks."""
    parser = EpubParser()
    html = (
        "<blockquote>Q</blockquote>"
        "<pre>code line</pre>"
        "<table><tr><td>cell</td></tr></table>"
        "<figure><figcaption>Cap</figcaption></figure>"
    )
    cleaned = parser.clean_html(html)
    assert "Q" in cleaned
    assert "code line" in cleaned
    assert "cell" in cleaned
    assert "Cap" in cleaned


def test_epub_parser_parse_raises_for_missing_file() -> None:
    parser = EpubParser()
    try:
        parser.parse("missing.epub")
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised is True


def test_epub_parser_parse_returns_parsedbook_for_minimal_book() -> None:
    # Detailed parsing scenarios are covered in T06.
    parser = EpubParser()
    result = parser.parse_book_content(
        title="My Book",
        author="Me",
        chapter_payloads=[("Chapter 1", "<p>First</p><p>Second</p>")],
    )
    assert isinstance(result, ParsedBook)
    assert result.title == "My Book"
    assert len(result.chapters) == 1
    assert "First" in result.chapters[0].content


def test_epub_parser_parses_valid_epub_with_chapters(tmp_path: Path) -> None:
    parser = EpubParser()
    epub_path = tmp_path / "sample.epub"

    book = epub.EpubBook()
    book.set_identifier("id123")
    book.set_title("Sample EPUB")
    book.set_language("en")
    book.add_author("Author A")

    c1 = epub.EpubHtml(title="One", file_name="chap_1.xhtml", content="<h1>One</h1><p>Alpha text.</p>")
    c2 = epub.EpubHtml(title="Two", file_name="chap_2.xhtml", content="<h1>Two</h1><p>Beta text.</p>")
    book.add_item(c1)
    book.add_item(c2)
    book.toc = (c1, c2)
    book.spine = ["nav", c1, c2]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(epub_path), book)

    parsed = parser.parse(str(epub_path))
    assert parsed.title == "Sample EPUB"
    assert parsed.author == "Author A"
    joined = " ".join(ch.content for ch in parsed.chapters)
    assert "Alpha text." in joined
    assert "Beta text." in joined


def test_epub_parser_handles_malformed_epub(tmp_path: Path) -> None:
    parser = EpubParser()
    bad_path = tmp_path / "bad.epub"
    bad_path.write_text("not a real epub", encoding="utf-8")

    try:
        parser.parse(str(bad_path))
        raised = False
    except Exception:
        raised = True

    assert raised is True
