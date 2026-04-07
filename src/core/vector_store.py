from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError


class VectorStore:
    def __init__(self, persist_directory: str = "data/chroma") -> None:
        self.persist_directory = persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)

    def create_collection(self, collection_name: str):  # type: ignore[no-untyped-def]
        return self.client.get_or_create_collection(name=collection_name)

    def list_collections(self) -> list:  # type: ignore[type-arg]
        return self.client.list_collections()

    def delete_collection(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(name=collection_name)
        except NotFoundError:
            # Deleting an unknown collection should be idempotent for callers.
            return

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        collection = self.create_collection(collection_name)
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(self, collection_name: str, query_embedding: list[float], n_results: int = 5) -> dict:
        collection = self.create_collection(collection_name)
        return collection.query(query_embeddings=[query_embedding], n_results=n_results)
