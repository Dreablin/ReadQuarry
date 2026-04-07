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
