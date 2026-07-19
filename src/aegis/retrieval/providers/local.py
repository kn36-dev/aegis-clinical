"""
LocalVectorQueryProvider

Read-side counterpart to ``aegis.vectorstores.local.LocalVectorStore``, the
same way ``retrieval/providers/upstash.py`` is the read-side counterpart to
``vectorstores/upstash.py``. ``LocalVectorStore`` is the offline indexing
pipeline's in-memory write path (index, index_many, delete); this adapter is
the runtime query path used by ``RetrievalService`` when it needs semantic
search without a live Upstash Vector index -- today, exclusively the
deterministic local retrieval-evaluation mode in ``aegis.evaluation``.

Performs a brute-force cosine similarity scan in pure Python (no numpy
dependency introduced solely for this adapter) -- appropriate for the small,
hand-curated evaluation fixture this is built for, not a production-scale
index.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from aegis.retrieval.providers.base import VectorMatch, VectorQueryProvider

if TYPE_CHECKING:
    from aegis.vectorstores.local import LocalVectorStore


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalVectorQueryProvider(VectorQueryProvider):
    """
    ``VectorQueryProvider`` over an already-populated ``LocalVectorStore``.

    Stateless aside from the injected store: given the same store contents
    and query embedding, always returns the same ranked ``VectorMatch`` list.
    """

    def __init__(self, store: LocalVectorStore) -> None:
        self._store = store

    def query(
        self,
        embedding: list[float],
        top_k: int,
    ) -> list[VectorMatch]:
        scored = [
            (_cosine_similarity(embedding, document.embedding), document)
            for document in self._store.all()
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        return [
            VectorMatch(
                id=document.representation.concept_id,
                score=score,
                metadata=document.representation.metadata.model_dump(),
            )
            for score, document in scored[:top_k]
        ]
