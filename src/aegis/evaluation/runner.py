"""
Evaluation run orchestration.

Resolves concrete collaborators the same way ``aegis.api.bootstrap`` does
for the real application -- reusing ``get_settings()``,
``build_embedding_provider``, ``build_vector_query_provider``,
``validate_embedding_compatibility``, and ``build_reasoning_provider`` --
and wires them into ``RetrievalEvaluator``/``ReasoningEvaluator``. Selects
*which* backend to use per ``EvaluationConfig.retrieval.mode``; never
reimplements provider construction itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aegis.api.bootstrap import (
    EmbeddingConfiguration,
    build_embedding_provider,
    build_reasoning_provider,
    build_vector_query_provider,
    open_clinical_connection,
    validate_embedding_compatibility,
)
from aegis.config import get_settings
from aegis.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from aegis.evaluation.dataset import load_clinical_cases
from aegis.evaluation.local_index import build_local_vector_query_provider
from aegis.evaluation.rate_limiter import RateLimitedReasoningProvider, RateLimiter
from aegis.evaluation.reasoning_eval import ReasoningEvaluator, ReasoningReport
from aegis.evaluation.retrieval_eval import RetrievalEvaluator, RetrievalReport
from aegis.infrastructure.crewai.reasoning_provider import CrewAIReasoningProvider
from aegis.services.clinical_reasoning_service import DefaultClinicalReasoningService
from aegis.services.context_assembler import DefaultContextAssembler
from aegis.services.retrieval_service import DefaultRetrievalService

if TYPE_CHECKING:
    from aegis.embeddings.base import EmbeddingProvider
    from aegis.evaluation.config import EvaluationConfig
    from aegis.retrieval.providers.base import VectorQueryProvider
    from aegis.services.retrieval_service import RetrievalService


def _build_retrieval_service(config: EvaluationConfig) -> tuple[RetrievalService, str]:
    """
    Build the real ``RetrievalService`` for ``config.retrieval.mode``.

    Deliberately branches *before* touching ``aegis.config.get_settings()``:
    ``AppSettings`` unconditionally requires Upstash Vector credentials in
    every profile (see its docstring), so local/CI mode must never call it
    -- it builds its own ``SentenceTransformersEmbeddingProvider`` directly
    from ``config.retrieval.local_embedding_model`` instead, keeping it
    genuinely credential-free. Production mode uses the real settings and
    ``aegis.api.bootstrap`` provider construction, exactly like the app.
    """
    if config.retrieval.mode == "local":
        embedding_provider: EmbeddingProvider = SentenceTransformersEmbeddingProvider(
            model_name=config.retrieval.local_embedding_model
        )
        # The same embedding_provider instance both builds the fixture
        # index and embeds queries, so dimensions always agree by
        # construction -- no compatibility check needed (unlike
        # production, where the index already exists independently).
        vector_query_provider: VectorQueryProvider = build_local_vector_query_provider(
            config.retrieval.local_fixture_csv, embedding_provider
        )
        backend_label = f"local (fixture: {config.retrieval.local_fixture_csv})"
        return DefaultRetrievalService(embedding_provider, vector_query_provider), backend_label

    settings = get_settings()
    embedding_config = EmbeddingConfiguration.from_settings(settings)
    embedding_provider = build_embedding_provider(embedding_config, settings)

    # Only AEGIS_PROFILE=demo-local's branch of build_vector_query_provider
    # actually reads from this connection (to compile/load the local
    # vector index); every other profile still queries the real Upstash
    # Vector index and ignores it. Opened and closed here rather than
    # threaded through EvaluationConfig, since nothing downstream of
    # vector_query_provider construction needs it to stay open.
    connection = open_clinical_connection(settings)
    try:
        vector_query_provider = build_vector_query_provider(
            settings, connection, embedding_provider
        )
    finally:
        connection.close()

    validate_embedding_compatibility(embedding_config, embedding_provider, vector_query_provider)

    return DefaultRetrievalService(
        embedding_provider, vector_query_provider
    ), "production (upstash)"


def _build_retrieval_evaluator(config: EvaluationConfig) -> tuple[RetrievalEvaluator, str]:
    retrieval_service, backend_label = _build_retrieval_service(config)
    cases = load_clinical_cases(config.dataset_path)
    evaluator = RetrievalEvaluator(
        retrieval_service=retrieval_service,
        cases=cases,
        top_k_values=config.retrieval.top_k_values,
        similarity_threshold=config.retrieval.similarity_threshold,
    )
    return evaluator, backend_label


def run_retrieval_evaluation(config: EvaluationConfig) -> tuple[RetrievalReport, str]:
    """Run retrieval evaluation, returning the report and its retrieval-backend label."""
    evaluator, backend_label = _build_retrieval_evaluator(config)
    return evaluator.evaluate(), backend_label


async def run_reasoning_evaluation(config: EvaluationConfig) -> tuple[ReasoningReport, str, str]:
    """
    Run reasoning evaluation, returning the report, the retrieval-backend
    label, and model/provider info -- both needed for provenance.

    Internally runs the configured retrieval step (per
    ``config.retrieval.mode``) to supply each case's real evidence, since
    the reasoning boundary is
    ``NormalizedClinicalNote + RetrievalResult -> ClinicalReasoningService``,
    never a fabricated context.
    """
    retrieval_evaluator, backend_label = _build_retrieval_evaluator(config)
    cases = load_clinical_cases(config.dataset_path)

    settings = get_settings()
    reasoning_provider = build_reasoning_provider(settings)
    model_provider_info = (
        f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL} (profile={settings.AEGIS_PROFILE})"
    )

    # Only the real Groq-backed provider needs throttling; the demo
    # profile's deterministic provider makes no external calls.
    if isinstance(reasoning_provider, CrewAIReasoningProvider):
        reasoning_provider = RateLimitedReasoningProvider(
            reasoning_provider, RateLimiter(config.rate_limit)
        )

    reasoning_model_name = config.reasoning.reasoning_model or settings.LLM_MODEL
    reasoning_service = DefaultClinicalReasoningService(reasoning_provider, reasoning_model_name)
    context_assembler = DefaultContextAssembler()

    evaluator = ReasoningEvaluator(retrieval_evaluator, context_assembler, reasoning_service)
    report = await evaluator.evaluate(cases)
    return report, backend_label, model_provider_info
