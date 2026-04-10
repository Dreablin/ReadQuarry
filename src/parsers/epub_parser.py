import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from ebooklib import ITEM_DOCUMENT, epub

_EXTRACT_BLOCK_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "dd",
        "dt",
        "figcaption",
        "td",
        "th",
        "pre",
        "div",
    }
)


def _has_inner_extractable_block(element: Tag) -> bool:
    """True if ``element`` contains another tag we extract (avoids double-counting)."""
    for node in element.descendants:
        if node is element:
            continue
        if isinstance(node, Tag) and node.name in _EXTRACT_BLOCK_TAGS:
            return True
    return False

from src.parsers.base import BaseParser, ParsedBook, ParsedChapter


class EpubParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".epub")

    def supported_extensions(self) -> list[str]:
        return [".epub"]

    def clean_html(self, html: str) -> str:
        """Strip tags while keeping paragraph-sized breaks for chunking strategies.

        Pull text from block-level tags (paragraphs, headings, list items, tables,
        quotes, leaf ``div`` wrappers used by some EPUBs, etc.). Only **leaf**
        extractable nodes are kept (no inner extractable descendant), so a
        ``<p>`` inside ``<blockquote>`` is emitted once. If nothing matches, fall
        back to full-document extraction with double-newline separators (BUGS.md B04).
        """
        soup = BeautifulSoup(html, "html.parser")
        blocks: list[str] = []
        for tag in soup.find_all(list(_EXTRACT_BLOCK_TAGS)):
            if not isinstance(tag, Tag):
                continue
            if _has_inner_extractable_block(tag):
                continue
            piece = " ".join(tag.get_text(separator=" ", strip=True).split())
            if piece:
                blocks.append(piece)
        if blocks:
            return "\n\n".join(blocks)
        text = soup.get_text(separator="\n\n", strip=True)
        merged: list[str] = []
        for block in re.split(r"\n\s*\n+", text):
            line = " ".join(block.split())
            if line:
                merged.append(line)
        return "\n\n".join(merged)

    def parse_book_content(
        self,
        title: str,
        author: str | None,
        chapter_payloads: list[tuple[str, str]],
    ) -> ParsedBook:
        chapters: list[ParsedChapter] = []
        for index, (chapter_title, chapter_html) in enumerate(chapter_payloads):
            cleaned = self.clean_html(chapter_html)
            if not cleaned:
                continue
            chapters.append(
                ParsedChapter(
                    title=chapter_title or f"Chapter {index + 1}",
                    content=cleaned,
                    index=index,
                )
            )
        return ParsedBook(title=title, author=author, chapters=chapters)

    def parse(self, file_path: str) -> ParsedBook:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)
        if not self.can_parse(file_path):
            raise ValueError(f"Unsupported file type for EpubParser: {file_path}")

        book = epub.read_epub(file_path)
        title = (book.get_metadata("DC", "title") or [("Untitled", {})])[0][0] or "Untitled"
        author_meta = book.get_metadata("DC", "creator")
        author = author_meta[0][0] if author_meta else None

        payloads: list[tuple[str, str]] = []
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            chapter_title = item.get_name() or "Chapter"
            html = item.get_content().decode("utf-8", errors="ignore")
            payloads.append((chapter_title, html))

        return self.parse_book_content(title=title, author=author, chapter_payloads=payloads)
