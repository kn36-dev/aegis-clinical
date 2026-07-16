"""
Application Bootstrap Layer.

Owns the runtime composition step between ``AppSettings`` and a running
FastAPI application: opening the clinical registry SQLite connection,
constructing concrete infrastructure adapters from configuration,
validating the embedding/vector-index compatibility boundary, and
assembling the ``AegisContainer`` those adapters back. ``api/main.py``'s
lifespan calls this module and stores the results on ``app.state`` --
this module never touches ``app`` or FastAPI itself, and never
performs clinical reasoning, retrieval, persistence, or workflow
routing (all of that stays owned by the application services this
container assembles, per ``aegis.application.container``).

Nothing here introduces new business logic: every adapter constructed
below already exists (``aegis.infrastructure.*``, ``aegis.embeddings.*``,
``aegis.retrieval.providers.upstash``); this module only decides,
entirely from ``AppSettings``, which concrete instance to build.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aegis.application.container import AegisContainer, build_container
from aegis.database.database import init_clinical_database
from aegis.database.repositories.icd_repository import ICDRepository
from aegis.embeddings.openai import OpenAIEmbeddingProvider
from aegis.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from aegis.infrastructure.crewai.reasoning_provider import CrewAIReasoningProvider
from aegis.infrastructure.sqlite.icd_code_validator import SQLiteICDCodeValidator
from aegis.infrastructure.upstash.clinical_decision_cache_repository import (
    UpstashClinicalDecisionCacheRepository,
)
from aegis.retrieval.providers.upstash import UpstashVectorQueryProvider

if TYPE_CHECKING:
    from aegis.config import AppSettings
    from aegis.embeddings.base import EmbeddingProvider
    from aegis.retrieval.providers.base import VectorQueryProvider

_KNOWN_EMBEDDING_PROVIDERS = ("openai", "sentence_transformers")


class EmbeddingCompatibilityError(RuntimeError):
    """
    Raised when the configured ``EmbeddingProvider`` and
    ``VectorQueryProvider`` disagree on vector shape, or when
    ``EMBEDDING_PROVIDER`` names an adapter this bootstrap does not
    know how to construct.

    Raising this during startup (rather than letting a shape mismatch
    surface later as an opaque Upstash query error) is the point: a
    query embedded into the wrong vector space would not error loudly,
    it would just return semantically meaningless matches.
    """


@dataclass(frozen=True)
class EmbeddingConfiguration:
    """
    Runtime infrastructure configuration for the embedding <-> vector
    index compatibility boundary.

    This is not a domain model -- it is a typed carrier for the three
    settings (``EMBEDDING_PROVIDER``, ``EMBEDDING_MODEL``,
    ``EMBEDDING_DIMENSIONS``) the composition root uses to build a
    matching ``EmbeddingProvider`` and to verify it actually agrees
    with the configured ``VectorQueryProvider`` before the application
    accepts traffic. Introduced so the two providers are always
    reasoned about together as a single compatibility boundary, never
    as independent, individually-defaulted settings.
    """

    provider: str
    model: str
    dimensions: int

    @classmethod
    def from_settings(cls, settings: AppSettings) -> EmbeddingConfiguration:
        return cls(
            provider=settings.EMBEDDING_PROVIDER,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )


def build_embedding_provider(
    config: EmbeddingConfiguration, settings: AppSettings
) -> EmbeddingProvider:
    """
    Construct the ``EmbeddingProvider`` named by ``config.provider``.

    Configuration is the only selector -- this never inspects the
    target vector index, falls back to a different provider, or infers
    a provider from anything other than ``EMBEDDING_PROVIDER`` itself.
    """
    if config.provider == "openai":
        if settings.OPENAI_API_KEY is None:
            raise EmbeddingCompatibilityError(
                "EMBEDDING_PROVIDER is 'openai' but OPENAI_API_KEY is not configured."
            )
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY.get_secret_value(),
            model=config.model,
        )
    if config.provider == "sentence_transformers":
        return SentenceTransformersEmbeddingProvider(model_name=config.model)

    raise EmbeddingCompatibilityError(
        f"Unknown EMBEDDING_PROVIDER {config.provider!r}. "
        f"Expected one of {_KNOWN_EMBEDDING_PROVIDERS!r}."
    )


def build_vector_query_provider(settings: AppSettings) -> VectorQueryProvider:
    """Construct the Upstash Vector runtime query adapter from settings."""
    return UpstashVectorQueryProvider(
        url=str(settings.UPSTASH_VECTOR_REST_URL),
        token=settings.UPSTASH_VECTOR_REST_TOKEN.get_secret_value(),
    )


def validate_embedding_compatibility(
    config: EmbeddingConfiguration,
    embedding_provider: EmbeddingProvider,
    vector_query_provider: VectorQueryProvider,
) -> None:
    """
    Fail fast if the configured ``EmbeddingProvider`` and
    ``VectorQueryProvider`` would put query and indexed vectors in
    different vector spaces.

    Two checks, both required to pass:

    1. The ``EmbeddingProvider`` is actually probed (never trusting
       ``EMBEDDING_DIMENSIONS`` blindly) by embedding a fixed probe
       string and measuring the real output dimensionality.
    2. When the concrete ``VectorQueryProvider`` exposes index
       introspection (today: ``UpstashVectorQueryProvider.
       get_index_dimension``; duck-typed rather than required so other
       backends without introspection are not forced to implement it),
       the live index's declared dimension is cross-checked too.

    Raises ``EmbeddingCompatibilityError`` on any mismatch. Never
    silently substitutes a different provider or infers one from the
    index -- configuration remains the single source of truth for
    *selection*; this function only verifies that selection is
    internally consistent.
    """
    probe_vector = embedding_provider.embed_query("aegis-embedding-compatibility-probe")
    actual_dimensions = len(probe_vector)

    if actual_dimensions != config.dimensions:
        raise EmbeddingCompatibilityError(
            f"EMBEDDING_DIMENSIONS is configured as {config.dimensions}, but the "
            f"configured EmbeddingProvider ({config.provider}, model={config.model!r}) "
            f"actually produces {actual_dimensions}-dimensional vectors. Refusing to start."
        )

    get_index_dimension = getattr(vector_query_provider, "get_index_dimension", None)
    if get_index_dimension is None:
        return

    index_dimensions = get_index_dimension()
    if index_dimensions != config.dimensions:
        raise EmbeddingCompatibilityError(
            f"EMBEDDING_DIMENSIONS is configured as {config.dimensions}, but the target "
            f"vector index actually reports {index_dimensions} dimensions. The configured "
            "EmbeddingProvider and the live Upstash index disagree on vector shape -- "
            "refusing to start."
        )


def open_clinical_connection(settings: AppSettings) -> sqlite3.Connection:
    """
    Run the ordered clinical-registry migrations (idempotent -- every
    migration is ``CREATE TABLE IF NOT EXISTS``, so this is safe to run
    on every startup without dropping existing data) and open a
    long-lived connection with the project's standard PRAGMAs applied.

    The caller (``api/main.py``'s lifespan) owns closing this
    connection at shutdown.
    """
    init_clinical_database(settings.CLINICAL_DB_PATH)

    connection = sqlite3.connect(settings.CLINICAL_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA busy_timeout=30000;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def build_infrastructure(settings: AppSettings, connection: sqlite3.Connection) -> AegisContainer:
    """
    Construct every infrastructure adapter from ``settings``, validate
    the embedding/vector-index compatibility boundary, and assemble the
    full ``AegisContainer``.

    Raises ``EmbeddingCompatibilityError`` immediately -- before
    ``build_container`` is ever called -- if the configured embedding
    provider and vector index disagree on vector shape.
    """
    embedding_config = EmbeddingConfiguration.from_settings(settings)
    embedding_provider = build_embedding_provider(embedding_config, settings)
    vector_query_provider = build_vector_query_provider(settings)
    validate_embedding_compatibility(embedding_config, embedding_provider, vector_query_provider)

    cache_repository = UpstashClinicalDecisionCacheRepository(
        url=str(settings.UPSTASH_REDIS_REST_URL),
        token=settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value(),
        ttl_seconds=settings.CACHE_TTL_SECONDS,
    )
    icd_code_validator = SQLiteICDCodeValidator(ICDRepository(connection))
    reasoning_provider = CrewAIReasoningProvider(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        temperature=settings.REASONING_TEMPERATURE,
    )

    return build_container(
        connection,
        cache_repository=cache_repository,
        embedding_provider=embedding_provider,
        vector_query_provider=vector_query_provider,
        reasoning_provider=reasoning_provider,
        reasoning_model_name=settings.LLM_MODEL,
        icd_code_validator=icd_code_validator,
    )
