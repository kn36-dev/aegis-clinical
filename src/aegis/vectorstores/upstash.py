from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from aegis.indexing.documents import VectorDocument

from upstash_vector import Index

from aegis.vectorstores.base import VectorStore


class UpstashVectorStore(VectorStore):
    """
    Upstash Vector implementation.

    Responsible only for persistence and retrieval of vectors.
    """

    def __init__(
        self,
        url: str,
        token: str,
    ) -> None:

        self._index = Index(
            url=url,
            token=token,
        )

    def index(
        self,
        document: VectorDocument,
    ) -> None:

        self._index.upsert(
            vectors=[
                (
                    document.representation.concept_id,
                    document.embedding,
                    document.representation.metadata.model_dump(),
                )
            ]
        )

    def index_many(
        self,
        documents: Iterable[VectorDocument],
    ) -> None:

        vectors = [
            (
                document.representation.concept_id,
                document.embedding,
                document.representation.metadata.model_dump(),
            )
            for document in documents
        ]

        if vectors:
            self._index.upsert(vectors=vectors)

    def delete(
        self,
        concept_id: str,
    ) -> None:

        self._index.delete(ids=[concept_id])
