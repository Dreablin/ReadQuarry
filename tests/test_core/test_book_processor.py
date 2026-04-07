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


def test_book_processor_integration_with_real_services(tmp_path) -> None:
    from src.core.embeddings import EmbeddingService
    from src.core.search_engine import SearchEngine
    from src.core.vector_store import VectorStore

    class IntegrationParser:
        def parse(self, _file_path: str) -> ParsedBook:
            return ParsedBook(
                title="Integration Book",
                author="Tester",
                chapters=[
                    ParsedChapter(title="Chapter A", content="Alpha rabbit.\n\nBeta rabbit.", index=0),
                    ParsedChapter(title="Chapter B", content="Gamma fox.", index=1),
                ],
            )

    class IntegrationRegistry:
        def get_parser(self, _file_path: str):
            return IntegrationParser()

    processor = BookProcessor(
        parser_registry=IntegrationRegistry(),
        embedding_service=EmbeddingService(),
        vector_store=VectorStore(persist_directory=str(tmp_path / "chroma")),
        search_engine=SearchEngine(index_dir=str(tmp_path / "tantivy")),
    )

    result = processor.process_book(file_path="integration.epub", book_id=77, chunking_strategy="paragraph")
    assert result["book_title"] == "Integration Book"
    assert result["total_chunks"] >= 3


def test_book_processor_skips_storage_when_no_chunks() -> None:
    class EmptyParser:
        def parse(self, _file_path: str) -> ParsedBook:
            return ParsedBook(title="Empty", author=None, chapters=[ParsedChapter(title="C", content="", index=0)])

    class EmptyRegistry:
        def get_parser(self, _file_path: str):
            return EmptyParser()

    vector_store = DummyVectorStore()
    search_engine = DummySearchEngine()
    processor = BookProcessor(
        parser_registry=EmptyRegistry(),
        embedding_service=DummyEmbeddingService(),
        vector_store=vector_store,
        search_engine=search_engine,
    )

    result = processor.process_book(file_path="empty.epub", book_id=88, chunking_strategy="paragraph")
    assert result["total_chunks"] == 0
    assert vector_store.added is None
    assert search_engine.indexed is None
