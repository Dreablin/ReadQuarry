from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub

from src.parsers.base import BaseParser, ParsedBook, ParsedChapter


class EpubParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".epub")

    def supported_extensions(self) -> list[str]:
        return [".epub"]

    def clean_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

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
