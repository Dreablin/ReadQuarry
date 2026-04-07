from __future__ import annotations

from pathlib import Path
import shutil


class SearchEngine:
    """Lightweight exact-search wrapper with Tantivy-compatible interface."""

    def __init__(self, index_dir: str = "data/tantivy_index") -> None:
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._documents: list[dict] = []

    def index_documents(self, documents: list[dict]) -> None:
        for doc in documents:
            self._documents.append(
                {
                    "chunk_id": str(doc["chunk_id"]),
                    "text": str(doc["text"]),
                    "chapter": str(doc.get("chapter", "")),
                    "chunk_index": int(doc.get("chunk_index", 0)),
                }
            )

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        query_lower = query.strip().lower()
        if not query_lower:
            return []
        matched = [doc for doc in self._documents if query_lower in doc["text"].lower()]
        return matched[:max_results]

    def delete_index(self) -> None:
        self._documents = []
        if self.index_dir.exists():
            shutil.rmtree(self.index_dir, ignore_errors=True)
