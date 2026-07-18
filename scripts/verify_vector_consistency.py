#!/usr/bin/env python3
"""
One-time forensic check: does the vector currently stored in Upstash
Vector for a given ICD-11 code match the vector produced *right now*
by re-running the exact same representation-building and embedding
steps the offline indexing pipeline (``scripts/upload_index.py``) uses?

This is diagnostic only. It does not conclude whether the embedding
pipeline, the representation strategy, or the retrieval design is
correct -- it only reports the measured facts (dimensions, cosine
similarity, per-component differences) so a human can diagnose the
reported retrieval anomaly.

Neither existing Upstash adapter exposes fetching a vector's raw
stored values by id:

- ``aegis.vectorstores.upstash.UpstashVectorStore`` is write-only
  (index / index_many / delete) -- the offline upload path.
- ``aegis.retrieval.providers.upstash.UpstashVectorQueryProvider`` is
  query-only (nearest-neighbor search + index dimension introspection)
  -- the runtime read path ``RetrievalService`` uses.

This is a genuine capability gap in the current abstractions, not an
oversight to route around, and adding a `fetch`-by-id method to either
adapter would be a production API change -- out of scope for a forensic
script and explicitly disallowed here. This script therefore
constructs the underlying ``upstash_vector.Index`` SDK client directly,
scoped to this script only, using the same URL/token configuration
``build_vector_query_provider`` uses. This is the same pattern
``scripts/upload_index.py`` already uses to construct
``UpstashVectorStore`` directly from settings -- nothing in ``src/aegis``
is modified.

Usage:
    uv run python scripts/verify_vector_consistency.py [CODE]

    CODE defaults to "1A08" (the concept named in the reported anomaly).
"""

from __future__ import annotations

import math
import sqlite3
import sys

from pydantic import ValidationError
from upstash_vector import Index

from aegis.api.bootstrap import (
    EmbeddingCompatibilityError,
    EmbeddingConfiguration,
    build_embedding_provider,
)
from aegis.config import get_settings
from aegis.database.repositories.icd_repository import ICDRepository
from aegis.indexing.builders import RepresentationBuilder
from aegis.indexing.representations.structured_prose import StructuredProseRepresentation

DEFAULT_CODE = "1A08"
BANNER = "=" * 32


def fail(category: str, detail: str) -> None:
    print(f"\n[FAILED: {category}]\n{detail}\n")
    sys.exit(1)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def main() -> None:
    code = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CODE

    print(BANNER)
    print("AEGIS Vector Consistency Check")
    print(BANNER)

    try:
        settings = get_settings()
    except ValidationError as exc:
        fail("missing configuration", f"AppSettings failed to load:\n{exc}")
        return

    embedding_config = EmbeddingConfiguration.from_settings(settings)
    try:
        embedding_provider = build_embedding_provider(embedding_config, settings)
    except EmbeddingCompatibilityError as exc:
        fail("embedding provider construction", str(exc))
        return

    connection = sqlite3.connect(settings.CLINICAL_DB_PATH)
    try:
        record = ICDRepository(connection=connection).get_by_code(code)
        if record is None:
            fail(
                "concept not found",
                f"ICD code {code!r} was not found in {settings.CLINICAL_DB_PATH} "
                "(table icd11_taxonomy) -- cannot recompute a representation for a "
                "concept that is not in the authoritative source the indexing "
                "pipeline reads from.",
            )
            return

        representation = RepresentationBuilder(strategy=StructuredProseRepresentation()).build(
            record
        )

        print(f"\nCode:\n{code}")
        print(f"\nRepresentation source:\nSQLite ({settings.CLINICAL_DB_PATH}, icd11_taxonomy)")
        print(f"\nEmbedded text (recomputed now):\n{representation.metadata.embedded_text}")

        print(f"\nEmbedding provider class:\n{type(embedding_provider).__name__}")
        print(f"\nModel:\n{embedding_config.model}")

        local_vector = embedding_provider.embed_many([representation])[0].embedding
        print(f"\nLocal embedding:\ndimension={len(local_vector)}")

        print(f"\nUpstash index configuration:\n{settings.UPSTASH_VECTOR_REST_URL}")
        print("\nNamespace:\n<default> ('')")
        print(f"\nTarget vector ID:\n{code}")

        index = Index(
            url=str(settings.UPSTASH_VECTOR_REST_URL).rstrip("/"),
            token=settings.UPSTASH_VECTOR_REST_TOKEN.get_secret_value(),
        )

        try:
            results = index.fetch(ids=[code], include_vectors=True, include_metadata=True)
        except Exception as exc:
            fail(
                "Upstash fetch execution",
                f"index.fetch(ids=[{code!r}]) raised: {exc!r}. This means the "
                "comparison could not be completed with the current SDK usage -- "
                "it does not by itself indicate an embedding mismatch.",
            )
            return

        stored = results[0] if results else None
        if stored is None or stored.vector is None:
            fail(
                "vector not found in Upstash",
                f"No vector with a stored embedding exists in Upstash Vector for "
                f"id={code!r} in the default namespace. This means the concept was "
                "never indexed (or indexed under a different id/namespace), not "
                "that embeddings are inconsistent.",
            )
            return

        stored_vector = stored.vector
        stored_metadata = stored.metadata or {}
        stored_embedded_text = stored_metadata.get("embedded_text")

        print(f"\nStored vector:\ndimension={len(stored_vector)}")
        print(f"\nStored metadata embedded_text:\n{stored_embedded_text}")
        print(
            "\nEmbedded text identical (recomputed vs stored):\n"
            f"{representation.metadata.embedded_text == stored_embedded_text}"
        )

        if len(local_vector) != len(stored_vector):
            fail(
                "dimension mismatch",
                f"Local embedding has dimension {len(local_vector)}, but the "
                f"stored Upstash vector has dimension {len(stored_vector)}. Cosine "
                "similarity is not computable across mismatched dimensions.",
            )
            return

        similarity = cosine_similarity(local_vector, stored_vector)
        diffs = [abs(a - b) for a, b in zip(local_vector, stored_vector, strict=True)]
        max_diff = max(diffs)
        avg_diff = sum(diffs) / len(diffs)

        print(f"\nCosine similarity:\n{similarity:.6f}")
        print(f"\nMaximum difference:\n{max_diff:.6f}")
        print(f"\nAverage difference:\n{avg_diff:.6f}")
        print(f"\nResult:\n{'MATCH' if similarity > 0.999999 else 'MISMATCH'}")
        print(BANNER)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
