from dataclasses import dataclass

from src.parsers.base import BaseParser, ParsedBook, ParsedChapter, ParserRegistry


@dataclass
class DummyParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith(".dummy")

    def parse(self, file_path: str) -> ParsedBook:
        return ParsedBook(
            title="Dummy",
            author=None,
            chapters=[ParsedChapter(title="Ch1", content="Text", index=0)],
        )

    def supported_extensions(self) -> list[str]:
        return [".dummy"]


def test_registry_registers_and_resolves_parser() -> None:
    registry = ParserRegistry()
    parser = DummyParser()
    registry.register(parser)

    resolved = registry.get_parser("book.dummy")
    assert resolved is parser


def test_registry_raises_for_unsupported_file() -> None:
    registry = ParserRegistry()
    registry.register(DummyParser())

    try:
        registry.get_parser("book.epub")
        raised = False
    except ValueError:
        raised = True

    assert raised is True


def test_registry_reports_supported_extensions() -> None:
    registry = ParserRegistry()
    registry.register(DummyParser())
    assert registry.supported_extensions() == [".dummy"]
