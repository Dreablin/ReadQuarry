from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


class SearchEngine:
    """Lightweight exact-search wrapper with Tantivy-compatible interface."""

    def __init__(self, index_dir: str = "data/tantivy_index") -> None:
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self.index_dir / "documents.json"
        self._documents: list[dict] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self._store_path.is_file():
            return
        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(raw, list):
            return
        for item in raw:
            if isinstance(item, dict) and "chunk_id" in item and "text" in item:
                self._documents.append(
                    {
                        "chunk_id": str(item["chunk_id"]),
                        "text": str(item["text"]),
                        "chapter": str(item.get("chapter", "")),
                        "chunk_index": int(item.get("chunk_index", 0)),
                    }
                )

    def _persist(self) -> None:
        self._store_path.write_text(json.dumps(self._documents, ensure_ascii=False), encoding="utf-8")

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
        self._persist()

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        phrase_match = re.fullmatch(r'"(.+)"', query_lower)
        if phrase_match:
            phrase = phrase_match.group(1)
            matched = [doc for doc in self._documents if phrase in doc["text"].lower()]
            return matched[:max_results]

        terms = [t for t in re.split(r"\s+", query_lower) if t]
        scored: list[tuple[int, dict]] = []
        for doc in self._documents:
            text = doc["text"].lower()
            score = sum(text.count(term) for term in terms)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:max_results]]

    def delete_index(self) -> None:
        self._documents = []
        if self.index_dir.exists():
            shutil.rmtree(self.index_dir, ignore_errors=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self.index_dir / "documents.json"
