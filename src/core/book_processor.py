from __future__ import annotations

import logging
import time
from collections.abc import Callable, Generator
from typing import Any

from sqlalchemy.orm import Session

from src.core.chunking import (
    ChapterAwareRecursiveChunking,
    FixedSizeChunking,
    ParagraphChunking,
    SentenceChunking,
)
from src.models.chunk import Chunk

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, str | None], None]


class BookProcessor:
    def __init__(self, parser_registry, embedding_service, vector_store, search_engine) -> None:  # type: ignore[no-untyped-def]
        self.parser_registry = parser_registry
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.search_engine = search_engine

    def _get_chunker(
        self,
        strategy: str,
        *,
        chunk_size: int | None = None,
        overlap_ratio: float | None = None,
    ):  # type: ignore[no-untyped-def]
        if strategy == "fixed-size":
            size = 256 if chunk_size is None else max(1, int(chunk_size))
            ratio = 0.15 if overlap_ratio is None else float(overlap_ratio)
            return FixedSizeChunking(chunk_size=size, overlap_ratio=ratio)
        mapping = {
            "paragraph": ParagraphChunking(),
            "sentence": SentenceChunking(),
            "chapter-aware-recursive": ChapterAwareRecursiveChunking(),
        }
        return mapping.get(strategy, ParagraphChunking())

    @staticmethod
    def _emit_progress(
        on_progress: ProgressCallback | None,
        stage: str,
        progress: int,
        detail: str | None = None,
    ) -> tuple[str, int, str | None]:
        if on_progress:
            on_progress(stage, progress, detail)
        return (stage, progress, detail)

    def iter_ingestion(
        self,
        file_path: str,
        book_id: int,
        chunking_strategy: str = "paragraph",
        db: Session | None = None,
        *,
        chunk_size: int | None = None,
        overlap_ratio: float | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> Generator[tuple[str, int, str | None], None, dict[str, Any]]:
        """Parse, chunk, embed, and index a book, yielding ``(stage, progress, detail)`` tuples.

        Percent bands follow B01: parsing 0–20, chunking 20–40, embedding 40–80,
        indexing 80–95. The final return value matches :meth:`process_book`.
        """
        t0 = time.perf_counter()
        logger.info(
            "Ingestion start book_id=%s file_path=%s chunking_strategy=%s",
            book_id,
            file_path,
            chunking_strategy,
        )
        yield BookProcessor._emit_progress(on_progress, "parsing", 10, None)

        parser = self.parser_registry.get_parser(file_path)
        parser_name = type(parser).__name__
        parsed_book = parser.parse(file_path)
        n_chapters = len(parsed_book.chapters)
        logger.info(
            "Parsed book_id=%s parser=%s title=%r author=%r chapters=%d",
            book_id,
            parser_name,
            parsed_book.title,
            parsed_book.author,
            n_chapters,
        )
        yield BookProcessor._emit_progress(on_progress, "parsing", 20, None)

        chunker = self._get_chunker(
            chunking_strategy,
            chunk_size=chunk_size,
            overlap_ratio=overlap_ratio,
        )
        chunker_name = type(chunker).__name__
        chunks: list[dict] = []
        for chapter in parsed_book.chapters:
            chapter_chunks = chunker.chunk(
                chapter.content,
                metadata={
                    "book_id": book_id,
                    "chapter": chapter.title or f"Chapter {chapter.index + 1}",
                },
            )
            for chunk in chapter_chunks:
                chunks.append(chunk)

        logger.info(
            "Chunking book_id=%s strategy=%s chunker=%s total_chunks=%d",
            book_id,
            chunking_strategy,
            chunker_name,
            len(chunks),
        )
        yield BookProcessor._emit_progress(on_progress, "chunking", 30, None)

        texts = [c["text"] for c in chunks]
        if db is not None:
            chunk_rows: list[Chunk] = []
            for c in chunks:
                ch_title = c.get("chapter")
                chunk_rows.append(
                    Chunk(
                        book_id=book_id,
                        chapter_title=str(ch_title) if ch_title is not None else None,
                        chunk_index=int(c["chunk_index"]),
                        strategy=str(c["strategy"]),
                        text=c["text"],
                        paragraph_ids=None,
                    )
                )
            db.add_all(chunk_rows)
            db.flush()
            chunk_ids = [str(row.id) for row in chunk_rows]
        else:
            chunk_ids = [f"{book_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "book_id": c["book_id"],
                "chapter": c.get("chapter"),
                "chunk_index": c["chunk_index"],
                "strategy": c["strategy"],
            }
            for c in chunks
        ]

        yield BookProcessor._emit_progress(on_progress, "chunking", 40, None)

        if chunks:
            n_chunk = len(texts)
            yield BookProcessor._emit_progress(
                on_progress,
                "embedding",
                50,
                f"Embedding {n_chunk} chunks…",
            )
            logger.info("Embedding book_id=%s total_chunks=%d", book_id, len(texts))
            embeddings: list[list[float]] = []
            batch_size = 16
            for i in range(0, n_chunk, batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_emb = self.embedding_service.embed_texts(batch_texts)
                embeddings.extend(batch_emb)
                progress_pct = 50 + int((len(embeddings) / n_chunk) * 22)
                yield BookProcessor._emit_progress(
                    on_progress,
                    "embedding",
                    progress_pct,
                    f"Embedding {len(embeddings)} / {n_chunk} chunks…"
                )
            logger.info(
                "Embeddings ready book_id=%s vectors=%d dim=%d",
                book_id,
                len(embeddings),
                len(embeddings[0]) if embeddings else 0,
            )
            collection_name = f"book_{book_id}"
            self.vector_store.add_documents(
                collection_name=collection_name,
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(
                "ChromaDB book_id=%s collection=%s vectors_stored=%d",
                book_id,
                collection_name,
                len(chunk_ids),
            )
            yield BookProcessor._emit_progress(on_progress, "embedding", 72, None)

            index_docs = [
                {
                    "chunk_id": chunk_ids[i],
                    "text": texts[i],
                    "chapter": metadatas[i]["chapter"],
                    "chunk_index": metadatas[i]["chunk_index"],
                }
                for i in range(len(chunks))
            ]
            yield BookProcessor._emit_progress(on_progress, "indexing", 80, None)
            self.search_engine.index_documents(index_docs)
            index_path = str(self.search_engine.index_dir)
            logger.info(
                "SearchEngine index updated book_id=%s index_path=%s document_count=%d",
                book_id,
                index_path,
                len(index_docs),
            )
            yield BookProcessor._emit_progress(on_progress, "indexing", 90, None)
        else:
            logger.info(
                "Skipping embeddings and indexes book_id=%s (no chunks produced)",
                book_id,
            )
            yield BookProcessor._emit_progress(
                on_progress,
                "embedding",
                55,
                "No chunks produced; skipping embeddings",
            )
            yield BookProcessor._emit_progress(on_progress, "indexing", 85, None)

        elapsed = time.perf_counter() - t0
        logger.info(
            "Ingestion complete book_id=%s total_chunks=%d elapsed_seconds=%.3f",
            book_id,
            len(chunks),
            elapsed,
        )

        return {
            "book_id": book_id,
            "book_title": parsed_book.title,
            "book_author": parsed_book.author,
            "total_chunks": len(chunks),
            "chunking_strategy": chunking_strategy,
        }

    def process_book(
        self,
        file_path: str,
        book_id: int,
        chunking_strategy: str = "paragraph",
        db: Session | None = None,
        *,
        chunk_size: int | None = None,
        overlap_ratio: float | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Parse, chunk, embed, and index a book (blocking; no SSE).

        When ``db`` is provided, inserts one ``Chunk`` row per chunk before vector
        and index storage so RAG can resolve Chroma ids to SQLite text. Chroma and
        SearchEngine ids are set to ``str(chunk.id)``.
        """
        it = self.iter_ingestion(
            file_path,
            book_id,
            chunking_strategy,
            db,
            chunk_size=chunk_size,
            overlap_ratio=overlap_ratio,
            on_progress=on_progress,
        )
        try:
            while True:
                next(it)
        except StopIteration as ex:
            return ex.value
