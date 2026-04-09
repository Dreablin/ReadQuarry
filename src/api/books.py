from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config import settings
from src.api.settings import get_settings
from src.core.book_processor import BookProcessor
from src.core.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingService
from src.core.search_engine import SearchEngine
from src.core.vector_store import VectorStore
from src.db.database import get_db
from src.models.book import Book
from src.parsers import EpubParser, ParserRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books", tags=["books"])


def _parser_registry() -> ParserRegistry:
    reg = ParserRegistry()
    reg.register(EpubParser())
    return reg


def _book_to_response(book: Book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "file_name": book.file_name,
        "chunking_strategy": book.chunking_strategy,
        "upload_date": book.upload_date.isoformat() if book.upload_date else "",
    }


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    chunking_strategy: str = Form("paragraph"),
    db: Session = Depends(get_db),
) -> dict:
    allowed_strategies = {"paragraph", "sentence", "fixed-size", "chapter-aware-recursive"}
    if chunking_strategy not in allowed_strategies:
        raise HTTPException(status_code=400, detail="Unsupported chunking strategy")
    if not file.filename or not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="Only EPUB files are supported")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    existing = db.scalars(select(Book).where(Book.file_hash == file_hash)).first()
    if existing is not None:
        logger.warning(
            "Duplicate book upload rejected: file_hash=%s filename=%r",
            file_hash,
            file.filename,
        )
        raise HTTPException(status_code=409, detail="Book with this content already exists")

    stem = Path(file.filename).stem
    book = Book(
        title=stem,
        author=None,
        file_name=file.filename,
        file_hash=file_hash,
        chunking_strategy=chunking_strategy,
        total_paragraphs=None,
        total_chunks=None,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    book_id = book.id

    uploads_dir = settings.data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    destination = uploads_dir / f"{book_id}_{file.filename}"
    logger.info(
        "Saving upload book_id=%s path=%s size_bytes=%d filename=%r",
        book_id,
        str(destination),
        len(content),
        file.filename,
    )
    destination.write_bytes(content)
    logger.info("Saved EPUB to disk book_id=%s path=%s", book_id, str(destination))

    app_settings = get_settings()
    logger.info(
        "Starting book processing book_id=%s chunking_strategy=%s chroma_dir=%s index_parent=%s",
        book_id,
        chunking_strategy,
        str(settings.data_dir / "chroma"),
        str(settings.data_dir / "tantivy_index"),
    )
    processor = BookProcessor(
        parser_registry=_parser_registry(),
        embedding_service=EmbeddingService(
            model_name=str(app_settings.get("embedding_model") or DEFAULT_EMBEDDING_MODEL),
            device=str(app_settings.get("embedding_device") or "cpu"),
        ),
        vector_store=VectorStore(persist_directory=str(settings.data_dir / "chroma")),
        search_engine=SearchEngine(
            index_dir=str(settings.data_dir / "tantivy_index" / f"book_{book_id}")
        ),
    )
    try:
        result = processor.process_book(str(destination), book_id, chunking_strategy, db=db)
        logger.info(
            "Upload pipeline succeeded book_id=%s total_chunks=%s title=%r",
            book_id,
            result.get("total_chunks"),
            result.get("book_title"),
        )
    except Exception:
        logger.exception("Book processing failed for book_id=%s", book_id)
        destination.unlink(missing_ok=True)
        db.delete(book)
        db.commit()
        raise HTTPException(status_code=422, detail="Failed to process EPUB file") from None

    book.title = result.get("book_title") or book.title
    book.author = result.get("book_author")
    book.total_chunks = result.get("total_chunks")
    db.add(book)
    db.commit()
    db.refresh(book)
    return _book_to_response(book)


@router.get("")
def list_books(db: Session = Depends(get_db)) -> list[dict]:
    books = db.scalars(select(Book).order_by(Book.id.asc())).all()
    return [_book_to_response(b) for b in books]


@router.delete("")
def delete_all_books(db: Session = Depends(get_db)) -> dict:
    """Remove every book: SQLite rows (cascade), Chroma collections, search indices, upload files."""
    books = list(db.scalars(select(Book).order_by(Book.id.asc())).all())
    count = len(books)
    vs = VectorStore(persist_directory=str(settings.data_dir / "chroma"))
    uploads_dir = settings.data_dir / "uploads"
    for book in books:
        destination = uploads_dir / f"{book.id}_{book.file_name}"
        destination.unlink(missing_ok=True)
        vs.delete_collection(f"book_{book.id}")
        shutil.rmtree(settings.data_dir / "tantivy_index" / f"book_{book.id}", ignore_errors=True)
    if count:
        db.execute(delete(Book))
        db.commit()
    logger.info("Cleared all books: count=%d", count)
    return {"status": "cleared", "deleted_count": count}


@router.get("/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)) -> dict:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return _book_to_response(book)


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)) -> dict:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    uploads_dir = settings.data_dir / "uploads"
    destination = uploads_dir / f"{book_id}_{book.file_name}"
    destination.unlink(missing_ok=True)

    VectorStore(persist_directory=str(settings.data_dir / "chroma")).delete_collection(f"book_{book_id}")
    index_dir = settings.data_dir / "tantivy_index" / f"book_{book_id}"
    shutil.rmtree(index_dir, ignore_errors=True)

    db.delete(book)
    db.commit()
    return {"status": "deleted", "id": book_id}
