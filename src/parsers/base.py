from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParsedChapter:
    title: str | None
    content: str
    index: int


@dataclass
class ParsedBook:
    title: str
    author: str | None
    chapters: list[ParsedChapter]


class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Return True if this parser can handle the given file."""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedBook:
        """Extract text and metadata from the file."""

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser) -> None:
        self._parsers.append(parser)

    def get_parser(self, file_path: str) -> BaseParser:
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        raise ValueError(f"No parser available for file: {file_path}")

    def supported_extensions(self) -> list[str]:
        extensions: set[str] = set()
        for parser in self._parsers:
            extensions.update(parser.supported_extensions())
        return sorted(extensions)
