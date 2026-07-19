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
from aegis.indexing.local_compiler import compile_or_load_local_vector_store
from aegis.infrastructure.crewai.reasoning_provider import CrewAIReasoningProvider
from aegis.infrastructure.memory.clinical_decision_cache_repository import (
    FakeClinicalDecisionCacheRepository,
)
from aegis.infrastructure.memory.content_repository import FakeContentRepository
from aegis.infrastructure.memory.deterministic_reasoning_provider import (
    DeterministicTopCandidateReasoningProvider,
)
from aegis.infrastructure.sqlite.icd_code_validator import SQLiteICDCodeValidator
from aegis.infrastructure.upstash.clinical_decision_cache_repository import (
    UpstashClinicalDecisionCacheRepository,
)
from aegis.retrieval.providers.local import LocalVectorQueryProvider
from aegis.retrieval.providers.upstash import UpstashVectorQueryProvider

if TYPE_CHECKING:
    from aegis.config import AppSettings
    from aegis.embeddings.base import EmbeddingProvider
    from aegis.retrieval.providers.base import VectorQueryProvider
    from aegis.services.cache_service import ClinicalDecisionCacheRepository
    from aegis.services.clinical_reasoning_service import ReasoningProvider
    from aegis.services.normalization_service import ClinicalNoteContentRepository

_KNOWN_EMBEDDING_PROVIDERS = ("openai", "sentence_transformers")

# A small, fixed set of sample notes the demo and integration profiles
# can resolve content_reference against. This exists because of the
# documented "Live-Credential Content Seeding Gap"
# (docs/tradeoffs_and_limitations.md): the real SQLiteContentStore
# cannot associate content with a content_reference before
# ClinicalNoteService has generated a case_id, so a fresh submission
# against it always 502s regardless of profile. Callers (the demo
# profile's frontend, scripts/demo_e2e.py, scripts/integration_e2e.py)
# are expected to submit one of these known references rather than
# arbitrary freshly-minted ones.
DEMO_SAMPLE_NOTES: dict[str, str] = {
    "content-store://demo/acute-diarrhea": (
        "Patient presents with acute watery diarrhea and mild dehydration. "
        "No fever. No blood in stool. Onset 12 hours ago."
    ),
    "content-store://demo/productive-cough": (
        "Patient reports a productive cough with green sputum for five days, "
        "low-grade fever, and mild shortness of breath on exertion."
    ),
    "content-store://demo/migraine-with-aura": (
        "Patient describes recurrent unilateral throbbing headache preceded by "
        "visual aura, photophobia, and nausea, lasting several hours."
    ),
}

# Reasoning model identifier recorded on demo-profile CodingRecommendations.
# Distinct from settings.LLM_MODEL (which names the real Groq/Qwen model)
# so a persisted demo-profile record is never mistaken for a real LLM
# reasoning pass -- mirrors "fake-model" already used by
# scripts/demo_e2e.py and tests/integration/test_clinical_pipeline.py.
DEMO_REASONING_MODEL_NAME = "deterministic-demo-reasoning"


@dataclass(frozen=True)
class DemoPatientIdentity:
    """One fixed, deterministic patient_identity_vault row for the demo profile."""

    patient_id: str
    medical_record_number: str
    first_name: str
    last_name: str
    date_of_birth: str


# A small, fixed set of patient identities for the demo profile's physician
# submission UI to select from, in place of the random uuid4() patients
# scripts/e2e_common.py::_seed_patient_identity mints per e2e run. Those
# random ids make every demo run non-reproducible and give the frontend
# nothing stable to reference (see GET /api/v1/demo/patients in
# aegis.api.routers.demo). patient_id values are literal constants, never
# generated at runtime, so a demo run today references the exact same rows
# as a demo run next week.
DEMO_PATIENT_IDENTITIES: tuple[DemoPatientIdentity, ...] = (
    DemoPatientIdentity(
        patient_id="11111111-1111-4111-8111-111111111111",
        medical_record_number="MRN-DEMO-001",
        first_name="Jordan",
        last_name="Ellis",
        date_of_birth="1985-03-14",
    ),
    DemoPatientIdentity(
        patient_id="22222222-2222-4222-8222-222222222222",
        medical_record_number="MRN-DEMO-002",
        first_name="Priya",
        last_name="Nair",
        date_of_birth="1972-11-02",
    ),
    DemoPatientIdentity(
        patient_id="33333333-3333-4333-8333-333333333333",
        medical_record_number="MRN-DEMO-003",
        first_name="Miguel",
        last_name="Santos",
        date_of_birth="1990-07-21",
    ),
)


def seed_demo_patient_identities(connection: sqlite3.Connection, settings: AppSettings) -> None:
    """
    Idempotently seed ``DEMO_PATIENT_IDENTITIES`` into ``patient_identity_vault``
    when ``settings.AEGIS_PROFILE`` is ``"demo"`` or ``"demo-local"``; a
    no-op in every other profile.

    ``INSERT OR IGNORE`` against ``patient_id`` (the table's primary key)
    makes this safe to call on every startup -- exactly the same idempotency
    guarantee every numbered migration already relies on -- so re-running
    either profile never produces duplicate rows or requires a teardown
    step. Production and integration profiles are completely unaffected:
    this never runs outside "demo"/"demo-local", and never touches any
    row this doesn't own.
    """
    if settings.AEGIS_PROFILE not in ("demo", "demo-local"):
        return

    for identity in DEMO_PATIENT_IDENTITIES:
        connection.execute(
            """
            INSERT OR IGNORE INTO patient_identity_vault (
                patient_id,
                medical_record_number,
                first_name,
                last_name,
                date_of_birth
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                identity.patient_id,
                identity.medical_record_number,
                identity.first_name,
                identity.last_name,
                identity.date_of_birth,
            ),
        )
    connection.commit()


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
        # AppSettings.__init__ guarantees these three are populated by
        # the time a container is being built -- either explicitly, or
        # (AEGIS_PROFILE == "demo-local" only) defaulted -- and raises
        # during settings construction otherwise; the asserts only
        # narrow the Optional type for mypy.
        assert settings.EMBEDDING_PROVIDER is not None
        assert settings.EMBEDDING_MODEL is not None
        assert settings.EMBEDDING_DIMENSIONS is not None
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


def build_vector_query_provider(
    settings: AppSettings,
    connection: sqlite3.Connection,
    embedding_provider: EmbeddingProvider,
) -> VectorQueryProvider:
    """
    Construct the runtime ``VectorQueryProvider`` named by
    ``settings.AEGIS_PROFILE``.

    "demo-local" is the one profile that replaces retrieval itself: it
    compiles the real ICD-11 taxonomy (already seeded into
    ``connection`` by ``make db-seed-icd``) into a local, file-backed
    vector index via ``compile_or_load_local_vector_store`` -- see that
    function's docstring for the compile-once/reuse-after caching this
    relies on -- and serves queries from it with
    ``LocalVectorQueryProvider``. Every other profile queries the real
    Upstash Vector index identically to before.
    """
    if settings.AEGIS_PROFILE == "demo-local":
        assert settings.EMBEDDING_MODEL is not None
        assert settings.EMBEDDING_DIMENSIONS is not None
        store = compile_or_load_local_vector_store(
            connection,
            embedding_provider,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        )
        return LocalVectorQueryProvider(store)

    assert settings.UPSTASH_VECTOR_REST_URL is not None
    assert settings.UPSTASH_VECTOR_REST_TOKEN is not None
    return UpstashVectorQueryProvider(
        url=str(settings.UPSTASH_VECTOR_REST_URL).rstrip("/"),
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


def open_clinical_connection(
    settings: AppSettings,
) -> sqlite3.Connection:
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


def build_cache_repository(settings: AppSettings) -> ClinicalDecisionCacheRepository:
    """
    Construct the ``ClinicalDecisionCacheRepository`` named by
    ``settings.AEGIS_PROFILE``.

    Demo and demo-local profiles both use the deterministic in-memory
    adapter: cache-hit routing (``graphs.workflow._route_after_cache_lookup``)
    is demonstrated identically either way, since that edge is deterministic
    code operating on whatever ``CacheService`` reports, not on which
    concrete store backs it. Production and integration profiles both
    need the real Redis-backed adapter's persistence-across-restarts
    and shared-cache behavior -- integration exists specifically to
    verify that adapter against real infrastructure.

    Production and integration are given distinct Redis key namespaces
    (defaulting to the profile name itself, e.g. "production" /
    "integration") so the two environments cannot share a Redis
    instance and read or write each other's cached ``ClinicalDecision``
    entries -- see ``settings.REDIS_CACHE_NAMESPACE``. An explicit
    ``REDIS_CACHE_NAMESPACE`` overrides the profile-derived default.
    """
    if settings.AEGIS_PROFILE in ("demo", "demo-local"):
        return FakeClinicalDecisionCacheRepository()

    assert settings.UPSTASH_REDIS_REST_URL is not None
    assert settings.UPSTASH_REDIS_REST_TOKEN is not None
    return UpstashClinicalDecisionCacheRepository(
        url=str(settings.UPSTASH_REDIS_REST_URL),
        token=settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value(),
        ttl_seconds=settings.CACHE_TTL_SECONDS,
        namespace=settings.REDIS_CACHE_NAMESPACE or settings.AEGIS_PROFILE,
    )


def build_reasoning_provider(settings: AppSettings) -> ReasoningProvider:
    """
    Construct the ``ReasoningProvider`` named by ``settings.AEGIS_PROFILE``.

    Demo and demo-local profiles both use
    ``DeterministicTopCandidateReasoningProvider`` rather than
    Groq/CrewAI: it removes the one external dependency most likely to
    fail, rate-limit, or (for demo-local) require a credential at all,
    while still reasoning over the same real ``ReasoningContext``
    real retrieval produced -- see that class's docstring for why a
    naive hardcoded-code fake cannot satisfy
    ``ClinicalReasoningService``'s validation once retrieval is real.
    Production and integration profiles both use the real
    ``CrewAIReasoningProvider`` -- integration exists specifically to
    verify that adapter (and the Groq credential behind it) against
    real infrastructure.
    """
    if settings.AEGIS_PROFILE in ("demo", "demo-local"):
        return DeterministicTopCandidateReasoningProvider()

    assert settings.GROQ_API_KEY is not None
    return CrewAIReasoningProvider(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        temperature=settings.REASONING_TEMPERATURE,
    )


def build_content_repository(settings: AppSettings) -> ClinicalNoteContentRepository | None:
    """
    Construct the ``ClinicalNoteContentRepository`` override named by
    ``settings.AEGIS_PROFILE``, or ``None`` to let ``build_container``
    default to the real ``SQLiteContentStore``.

    Demo, demo-local, and integration profiles all substitute the
    in-memory adapter pre-seeded with ``DEMO_SAMPLE_NOTES`` -- see that
    constant's docstring for why this is not a demo/integration-mode
    preference but a workaround for the documented "Live-Credential
    Content Seeding Gap", which would block a fresh submission against
    the real ``SQLiteContentStore`` in any profile. "production" is
    left defaulting to the real store since it is not driven by an
    e2e script that submits fresh content on every run.
    """
    if settings.AEGIS_PROFILE in ("demo", "demo-local", "integration"):
        return FakeContentRepository(content_by_reference=DEMO_SAMPLE_NOTES)
    return None


def build_infrastructure(settings: AppSettings, connection: sqlite3.Connection) -> AegisContainer:
    """
    Construct every infrastructure adapter from ``settings``, validate
    the embedding/vector-index compatibility boundary, and assemble the
    full ``AegisContainer``.

    Embedding is constructed identically regardless of
    ``settings.AEGIS_PROFILE`` -- every profile uses a real
    ``EmbeddingProvider``, never a fake one. Vector retrieval is real
    Upstash Vector in every profile except "demo-local", which is
    branched inside ``build_vector_query_provider`` itself. ICD
    taxonomy validation is always real. ``build_cache_repository``,
    ``build_reasoning_provider``, ``build_content_repository``,
    ``build_vector_query_provider``, and ``seed_demo_patient_identities``
    each branch on profile in exactly one place.

    Raises ``EmbeddingCompatibilityError`` immediately -- before
    ``build_container`` is ever called -- if the configured embedding
    provider and vector index disagree on vector shape.
    """
    seed_demo_patient_identities(connection, settings)

    embedding_config = EmbeddingConfiguration.from_settings(settings)
    embedding_provider = build_embedding_provider(embedding_config, settings)
    vector_query_provider = build_vector_query_provider(settings, connection, embedding_provider)
    validate_embedding_compatibility(embedding_config, embedding_provider, vector_query_provider)

    icd_code_validator = SQLiteICDCodeValidator(ICDRepository(connection))

    return build_container(
        connection,
        cache_repository=build_cache_repository(settings),
        embedding_provider=embedding_provider,
        vector_query_provider=vector_query_provider,
        reasoning_provider=build_reasoning_provider(settings),
        reasoning_model_name=(
            DEMO_REASONING_MODEL_NAME
            if settings.AEGIS_PROFILE in ("demo", "demo-local")
            else settings.LLM_MODEL  # real model name for both production and integration
        ),
        icd_code_validator=icd_code_validator,
        content_repository=build_content_repository(settings),
    )
