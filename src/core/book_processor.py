from __future__ import annotations

import logging
import time

from src.core.chunking import (
    ChapterAwareRecursiveChunking,
    FixedSizeChunking,
    ParagraphChunking,
    SentenceChunking,
)

logger = logging.getLogger(__name__)


class BookProcessor:
    def __init__(self, parser_registry, embedding_service, vector_store, search_engine) -> None:  # type: ignore[no-untyped-def]
        self.parser_registry = parser_registry
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.search_engine = search_engine

    def _get_chunker(self, strategy: str):  # type: ignore[no-untyped-def]
        mapping = {
            "paragraph": ParagraphChunking(),
            "sentence": SentenceChunking(),
            "fixed-size": FixedSizeChunking(),
            "chapter-aware-recursive": ChapterAwareRecursiveChunking(),
        }
        return mapping.get(strategy, ParagraphChunking())

    def process_book(self, file_path: str, book_id: int, chunking_strategy: str = "paragraph") -> dict:
        t0 = time.perf_counter()
        logger.info(
            "Ingestion start book_id=%s file_path=%s chunking_strategy=%s",
            book_id,
            file_path,
            chunking_strategy,
        )
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

        chunker = self._get_chunker(chunking_strategy)
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

        texts = [c["text"] for c in chunks]
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

        if chunks:
            logger.info("Embedding book_id=%s batch_size=%d", book_id, len(texts))
            embeddings = self.embedding_service.embed_texts(texts)
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

            index_docs = [
                {
                    "chunk_id": chunk_ids[i],
                    "text": texts[i],
                    "chapter": metadatas[i]["chapter"],
                    "chunk_index": metadatas[i]["chunk_index"],
                }
                for i in range(len(chunks))
            ]
            self.search_engine.index_documents(index_docs)
            index_path = str(self.search_engine.index_dir)
            logger.info(
                "SearchEngine index updated book_id=%s index_path=%s document_count=%d",
                book_id,
                index_path,
                len(index_docs),
            )
        else:
            logger.info(
                "Skipping embeddings and indexes book_id=%s (no chunks produced)",
                book_id,
            )

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
