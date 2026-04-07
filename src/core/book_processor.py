from __future__ import annotations

from src.core.chunking import (
    ChapterAwareRecursiveChunking,
    FixedSizeChunking,
    ParagraphChunking,
    SentenceChunking,
)


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
        parser = self.parser_registry.get_parser(file_path)
        parsed_book = parser.parse(file_path)

        chunker = self._get_chunker(chunking_strategy)
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
            embeddings = self.embedding_service.embed_texts(texts)
            self.vector_store.add_documents(
                collection_name=f"book_{book_id}",
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            self.search_engine.index_documents(
                [
                    {
                        "chunk_id": chunk_ids[i],
                        "text": texts[i],
                        "chapter": metadatas[i]["chapter"],
                        "chunk_index": metadatas[i]["chunk_index"],
                    }
                    for i in range(len(chunks))
                ]
            )

        return {
            "book_id": book_id,
            "book_title": parsed_book.title,
            "book_author": parsed_book.author,
            "total_chunks": len(chunks),
            "chunking_strategy": chunking_strategy,
        }
