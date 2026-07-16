from __future__ import annotations

from upstash_vector import Index

from aegis.retrieval.providers.base import VectorMatch, VectorQueryProvider


class UpstashVectorQueryProvider(VectorQueryProvider):
    """
    Upstash Vector implementation of the runtime query path.

    Responsible only for semantic similarity lookup — never for
    indexing or deletion, which belong to
    ``aegis.vectorstores.upstash.UpstashVectorStore``.
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

    def get_index_dimension(self) -> int:
        """
        Report the target Upstash index's actual vector dimension.

        Best-effort introspection used only by the composition root's
        embedding/vector-index compatibility check -- not part of the
        ``VectorQueryProvider`` contract, since not every backend (e.g.
        pgvector, Qdrant) necessarily exposes this. Callers should
        duck-type-check for this method rather than assume it exists.
        """
        return self._index.info().dimension

    def query(
        self,
        embedding: list[float],
        top_k: int,
    ) -> list[VectorMatch]:

        results = self._index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
        )

        return [
            VectorMatch(
                id=result.id,
                score=result.score,
                metadata=result.metadata or {},
            )
            for result in results
        ]
