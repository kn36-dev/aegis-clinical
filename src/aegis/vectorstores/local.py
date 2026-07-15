from typing import Dict, Iterable, List

from aegis.indexing.documents import VectorDocument
from aegis.vectorstores.base import VectorStore


class LocalVectorStore(VectorStore):
    """
    In-memory vector store for deterministic local execution.

    Purpose:
    - local development
    - CI testing
    - reproducible indexing pipelines
    - evaluation without external dependencies

    NOT production scalable.
    """

    def __init__(self) -> None:
        # concept_id -> VectorDocument
        self._store: Dict[str, VectorDocument] = {}

    def index(self, document: VectorDocument) -> None:
        key = document.representation.concept_id
        self._store[key] = document

    def index_many(self, documents: Iterable[VectorDocument]) -> None:
        """
        Insert or overwrite vectors by concept_id.
        """
        for d in documents:
            key = d.representation.concept_id
            self._store[key] = d

    def upsert(self, vector: VectorDocument) -> None:
        concept_id = vector.representation.concept_id
        self._store[concept_id] = vector

    def get(self, concept_id: str) -> VectorDocument | None:
        return self._store.get(concept_id)

    def all(self) -> List[VectorDocument]:
        return list(self._store.values())

    def delete(self, concept_id: str) -> None:
        self._store.pop(concept_id, None)

    def count(self) -> int:
        return len(self._store)
