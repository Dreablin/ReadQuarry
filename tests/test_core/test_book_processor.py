from src.core.book_processor import BookProcessor
from src.parsers.base import ParsedBook, ParsedChapter


class DummyParser:
    def parse(self, file_path: str) -> ParsedBook:
        return ParsedBook(
            title="Demo",
            author="Author",
            chapters=[
                ParsedChapter(title="C1", content="One paragraph.\n\nSecond paragraph.", index=0),
            ],
        )


class DummyRegistry:
    def get_parser(self, _file_path: str):
        return DummyParser()


class DummyEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(i)] * 384 for i, _ in enumerate(texts, start=1)]


class DummyVectorStore:
    def __init__(self) -> None:
        self.added = None

    def add_documents(self, **kwargs) -> None:
        self.added = kwargs


class DummySearchEngine:
    def __init__(self) -> None:
        self.indexed = None

    def index_documents(self, docs: list[dict]) -> None:
        self.indexed = docs


def test_book_processor_runs_full_pipeline() -> None:
    vector_store = DummyVectorStore()
    search_engine = DummySearchEngine()
    processor = BookProcessor(
        parser_registry=DummyRegistry(),
        embedding_service=DummyEmbeddingService(),
        vector_store=vector_store,
        search_engine=search_engine,
    )

    result = processor.process_book(file_path="book.epub", book_id=42, chunking_strategy="paragraph")

    assert result["book_title"] == "Demo"
    assert result["book_id"] == 42
    assert result["total_chunks"] >= 1
    assert vector_store.added is not None
    assert vector_store.added["collection_name"] == "book_42"
    assert search_engine.indexed is not None
    assert len(search_engine.indexed) == result["total_chunks"]
