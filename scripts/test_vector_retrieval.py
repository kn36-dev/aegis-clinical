#!/usr/bin/env python3
"""
One-time operational verification of the production Upstash Vector
retrieval boundary.

Answers a single architectural validation question: does the
production Upstash Vector index return meaningful ICD-11 candidates
when queried with a real normalized clinical phrase, using the exact
same embedding provider and query adapter the application's
``RetrievalService`` uses at runtime?

This script is manually executed infrastructure verification, not
application behavior -- it is never imported by application code and
introduces no new architecture. It reuses, unmodified, the same
composition-root functions ``api/bootstrap.py`` uses to build the real
``EmbeddingProvider`` and ``VectorQueryProvider`` (including the
embedding/vector-index dimension compatibility check), so a pass here
means the real application would retrieve real candidates for this
query too.

Usage:
    uv run python scripts/test_vector_retrieval.py
"""

from __future__ import annotations

import sys

from pydantic import ValidationError

from aegis.api.bootstrap import (
    EmbeddingCompatibilityError,
    EmbeddingConfiguration,
    build_embedding_provider,
    build_vector_query_provider,
    validate_embedding_compatibility,
)
from aegis.config import get_settings

# QUERY_TEXT = "acute watery diarrhea with dehydration"
# QUERY_TEXT = "paratyphoid fever"
# QUERY_TEXT = "gastroenteritis"
QUERY_TEXT = """
ICD-11 Code: 1A04 
Classification Hierarchy: L1: Gastroenteritis or colitis of infectious origin | 
L2: Bacterial intestinal infections 
Clinical Term: Intestinal infections due to Clostridioides difficile"
"""

BANNER = "=" * 50


def fail(category: str, detail: str) -> None:
    print(f"\n[FAILED: {category}]\n{detail}\n")
    sys.exit(1)


def main() -> None:
    print(BANNER)
    print("AEGIS Vector Retrieval Verification")
    print(BANNER)

    try:
        settings = get_settings()
    except ValidationError as exc:
        fail(
            "missing configuration",
            "AppSettings failed to load -- Upstash Vector and/or embedding "
            "settings are missing from the environment/.env. Underlying error:\n"
            f"{exc}",
        )
        return

    embedding_config = EmbeddingConfiguration.from_settings(settings)

    try:
        embedding_provider = build_embedding_provider(embedding_config, settings)
    except EmbeddingCompatibilityError as exc:
        fail("embedding provider construction", str(exc))
        return

    try:
        vector_query_provider = build_vector_query_provider(settings)
    except Exception as exc:
        fail(
            "Upstash adapter construction",
            "Failed to construct the Upstash Vector query adapter -- check "
            "UPSTASH_VECTOR_REST_URL / UPSTASH_VECTOR_REST_TOKEN. "
            f"Underlying error: {exc!r}",
        )
        return

    try:
        validate_embedding_compatibility(
            embedding_config, embedding_provider, vector_query_provider
        )
    except EmbeddingCompatibilityError as exc:
        fail("embedding/index dimension mismatch", str(exc))
        return

    print(f"\nQuery:\n{QUERY_TEXT}")
    print(f"\nEmbedding:\n{embedding_config.provider} ({embedding_config.model})")

    try:
        query_embedding = embedding_provider.embed_query(QUERY_TEXT)
    except Exception as exc:
        fail("query embedding generation", f"embed_query() raised: {exc!r}")
        return

    try:
        matches = vector_query_provider.query(
            embedding=query_embedding,
            top_k=settings.RETRIEVAL_TOP_K,
        )
    except Exception as exc:
        fail(
            "Upstash query execution",
            "The query request to Upstash Vector failed. This usually means "
            "invalid credentials, an unreachable index, or a namespace/index "
            f"that does not match what was indexed. Underlying error: {exc!r}",
        )
        return

    if not matches:
        fail(
            "zero results",
            "Upstash Vector returned zero matches for this query. The index "
            "may be empty, the query may have landed in the wrong namespace, "
            "or the embedding/index vector spaces may be mismatched despite "
            "passing the dimension check above.",
        )
        return

    print("\nTop Results:\n")
    for position, match in enumerate(matches, start=1):
        metadata = match.metadata
        print(f"{position}.")
        print(f"Code:\n{metadata.get('code', match.id)}")
        print(f"\nTitle:\n{metadata.get('title', '<missing>')}")
        print(f"\nScore:\n{match.score}")
        print(f"\nMetadata:\n{metadata}")
        print()

    print(BANNER)
    print(
        f"Retrieval executed successfully: {len(matches)} candidate(s) returned. "
        "Judge clinical relevance of the results above manually -- see this script's "
        "usage notes for how to interpret them."
    )
    print(BANNER)


if __name__ == "__main__":
    main()
