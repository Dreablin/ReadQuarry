from __future__ import annotations

import json
import re
import shutil
from collections import Counter
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
        """Match using Unicode casefolding and word tokens (Latin, Cyrillic, etc.)."""
        raw = query.strip()
        if not raw:
            return []

        q_fold = raw.casefold()
        phrase_match = re.fullmatch(r'"(.+)"', q_fold)
        if phrase_match:
            phrase = phrase_match.group(1).strip()
            matched = [doc for doc in self._documents if phrase in doc["text"].casefold()]
            return matched[:max_results]

        terms = re.findall(r"\w+", q_fold, flags=re.UNICODE)
        if not terms:
            return []
        scored: list[tuple[int, dict]] = []
        for doc in self._documents:
            tokens = re.findall(r"\w+", doc["text"].casefold(), flags=re.UNICODE)
            ctr = Counter(tokens)
            score = sum(ctr[t] for t in terms)
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
