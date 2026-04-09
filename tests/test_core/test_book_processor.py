import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.core.book_processor import BookProcessor
from src.db.database import Base
from src.models.book import Book
from src.models.chunk import Chunk
from src.parsers.base import ParsedBook, ParsedChapter


def _memory_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


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
        self.index_dir = Path("dummy_tantivy_index")

    def index_documents(self, docs: list[dict]) -> None:
        self.indexed = docs


def test_book_processor_logs_ingestion_pipeline_stages(caplog: pytest.LogCaptureFixture) -> None:
    """B11: ingestion logs parser, chapters, chunks, ChromaDB, SearchEngine index, timing."""
    caplog.set_level(logging.INFO, logger="src.core.book_processor")
    vector_store = DummyVectorStore()
    search_engine = DummySearchEngine()
    processor = BookProcessor(
        parser_registry=DummyRegistry(),
        embedding_service=DummyEmbeddingService(),
        vector_store=vector_store,
        search_engine=search_engine,
    )
    processor.process_book(file_path="book.epub", book_id=42, chunking_strategy="paragraph")
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "book_id=42" in text
    assert "chapters=" in text or "chapter" in text.lower()
    assert "chunk" in text.lower()
    assert "ChromaDB" in text or "collection=book_42" in text
    assert "SearchEngine" in text or "index path" in text.lower()
    assert "elapsed" in text.lower() or "seconds" in text.lower()


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


def test_book_processor_persists_chunks_to_sqlite_when_db_provided() -> None:
    """B03: Chunk rows must exist in SQLite for RAG; Chroma ids match Chunk.id."""
    db = _memory_session()
    book = Book(
        title="Demo",
        author="Author",
        file_name="book.epub",
        file_hash="hash-b03-test",
        chunking_strategy="paragraph",
        total_paragraphs=None,
        total_chunks=None,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    vector_store = DummyVectorStore()
    search_engine = DummySearchEngine()
    processor = BookProcessor(
        parser_registry=DummyRegistry(),
        embedding_service=DummyEmbeddingService(),
        vector_store=vector_store,
        search_engine=search_engine,
    )
    result = processor.process_book(
        file_path="book.epub",
        book_id=book.id,
        chunking_strategy="paragraph",
        db=db,
    )
    db.commit()

    assert result["total_chunks"] >= 1
    assert db.query(Chunk).filter(Chunk.book_id == book.id).count() == result["total_chunks"]
    rows = db.query(Chunk).filter(Chunk.book_id == book.id).order_by(Chunk.id.asc()).all()
    assert vector_store.added is not None
    assert vector_store.added["ids"] == [str(r.id) for r in rows]
    for r in rows:
        assert r.text
        assert r.strategy == "paragraph"


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
