"""
Application Composition Root

Owns dependency assembly for the AEGIS runtime:

    Infrastructure Implementations
        -> Repository / Provider Interfaces
        -> Application Services
        -> LangGraph Runtime

No other layer is permitted to know how a concrete service, repository,
or provider is constructed. Services declare what they need through
constructor parameters typed as protocols/ABCs (``ClinicalNoteRepository``,
``PHIAnonymizer``, ``ReasoningProvider``, ...); this module is the only
place those parameters are bound to concrete objects. Nothing here
performs clinical reasoning, persistence, retrieval, or workflow
routing -- see the individual service modules for that behavior.

Visible seams: not every collaborator required by the eight application
services has a production implementation yet (``agents/crew`` is an
empty scaffold, no ``ICDCodeValidator`` implementation exists, and
Redis/Upstash wiring is a later phase -- see CLAUDE.md's Development
status). Rather than construct fakes or speculative adapters for those
gaps, ``build_container`` takes ``cache_repository``, ``embedding_provider``,
``vector_query_provider``, ``reasoning_provider``, and ``icd_code_validator``
as required parameters, so the caller (today: tests; later: a FastAPI
lifespan) supplies them explicitly. This keeps the missing infrastructure
visible as an explicit seam instead of hidden behind a default that looks
production-ready but is not. ``ClinicalNoteService``, ``NormalizationService``,
and ``PersistenceService`` have real SQLite/Presidio-backed adapters today,
so this module constructs those fully.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aegis.graphs.workflow import build_aegis_graph
from aegis.infrastructure.sqlite.clinical_decision_repository import (
    SQLiteClinicalDecisionRepository,
)
from aegis.infrastructure.sqlite.clinical_note_repository import SQLiteClinicalNoteRepository
from aegis.infrastructure.sqlite.content_store import SQLiteContentStore
from aegis.phi.presidio import PresidioPHIAnonymizer
from aegis.services.cache_service import DefaultCacheService
from aegis.services.clinical_decision_service import DefaultClinicalDecisionService
from aegis.services.clinical_note_service import DefaultClinicalNoteService
from aegis.services.clinical_reasoning_service import DefaultClinicalReasoningService
from aegis.services.context_assembler import DefaultContextAssembler
from aegis.services.normalization_service import DefaultNormalizationService
from aegis.services.persistence_service import DefaultPersistenceService
from aegis.services.retrieval_service import DefaultRetrievalService

if TYPE_CHECKING:
    import sqlite3

    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

    from aegis.embeddings.base import EmbeddingProvider
    from aegis.graphs.state import AegisWorkflowState
    from aegis.phi.base import PHIAnonymizer
    from aegis.retrieval.providers.base import VectorQueryProvider
    from aegis.services.cache_service import CacheService, ClinicalDecisionCacheRepository
    from aegis.services.clinical_decision_service import ClinicalDecisionService, ICDCodeValidator
    from aegis.services.clinical_note_service import ClinicalNoteService
    from aegis.services.clinical_reasoning_service import (
        ClinicalReasoningService,
        ReasoningPolicy,
        ReasoningProvider,
    )
    from aegis.services.context_assembler import ContextAssembler, ContextAssemblyPolicy
    from aegis.services.normalization_service import (
        ClinicalNoteContentRepository,
        NormalizationService,
    )
    from aegis.services.persistence_service import PersistenceService
    from aegis.services.retrieval_service import RetrievalService


@dataclass(frozen=True)
class AegisContainer:
    """
    Fully assembled AEGIS dependency graph.

    Fields are typed by the application-service/repository abstraction
    each object satisfies, not by its concrete implementation, so that
    holding a reference to this container never leaks which
    infrastructure backs a given capability. ``build_graph`` is a thin
    delegation to ``aegis.graphs.workflow.build_aegis_graph`` -- it does
    not duplicate or reinterpret orchestration logic, only supplies the
    services this container already assembled.
    """

    clinical_note_repository: SQLiteClinicalNoteRepository
    content_repository: ClinicalNoteContentRepository
    clinical_decision_repository: SQLiteClinicalDecisionRepository

    clinical_note_service: ClinicalNoteService
    normalization_service: NormalizationService
    cache_service: CacheService
    retrieval_service: RetrievalService
    context_assembler: ContextAssembler
    clinical_reasoning_service: ClinicalReasoningService
    clinical_decision_service: ClinicalDecisionService
    persistence_service: PersistenceService

    def build_graph(
        self,
        *,
        retrieval_top_k: int,
        retrieval_similarity_threshold: float | None = None,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
    ) -> CompiledStateGraph[AegisWorkflowState, Any, AegisWorkflowState, AegisWorkflowState]:
        """Compose the LangGraph workflow from this container's services."""
        return build_aegis_graph(
            self.clinical_note_service,
            self.normalization_service,
            self.cache_service,
            self.retrieval_service,
            self.context_assembler,
            self.clinical_reasoning_service,
            self.clinical_decision_service,
            self.persistence_service,
            retrieval_top_k=retrieval_top_k,
            retrieval_similarity_threshold=retrieval_similarity_threshold,
            checkpointer=checkpointer,
        )


def build_container(
    connection: sqlite3.Connection,
    *,
    cache_repository: ClinicalDecisionCacheRepository,
    embedding_provider: EmbeddingProvider,
    vector_query_provider: VectorQueryProvider,
    reasoning_provider: ReasoningProvider,
    reasoning_model_name: str,
    icd_code_validator: ICDCodeValidator,
    phi_anonymizer: PHIAnonymizer | None = None,
    content_repository: ClinicalNoteContentRepository | None = None,
    context_assembly_policy: ContextAssemblyPolicy | None = None,
    reasoning_policy: ReasoningPolicy | None = None,
) -> AegisContainer:
    """
    Assemble the full AEGIS dependency graph.

    ``connection`` is a single already-open connection to the clinical
    registry SQLite database (migrations 0001-0012) -- opening,
    migrating, and closing it is a deployment concern owned by the
    caller (``aegis-db``, a FastAPI lifespan, a test fixture), not by
    this composition root.

    ``cache_repository``, ``embedding_provider``, ``vector_query_provider``,
    ``reasoning_provider``, and ``icd_code_validator`` are required
    rather than defaulted: no production Redis, Upstash, CrewAI, or
    ICD-taxonomy-validating adapter exists yet (see module docstring),
    so this function does not fabricate one. ``phi_anonymizer`` and
    ``content_repository`` both have real production adapters
    (``PresidioPHIAnonymizer``, ``SQLiteContentStore``) and default to
    them, but remain overridable for callers that need a faster test
    double.
    """
    clinical_note_repository = SQLiteClinicalNoteRepository(connection)
    content_repository = content_repository or SQLiteContentStore(connection)
    clinical_decision_repository = SQLiteClinicalDecisionRepository(connection)

    clinical_note_service = DefaultClinicalNoteService(clinical_note_repository)
    normalization_service = DefaultNormalizationService(
        content_repository,
        phi_anonymizer or PresidioPHIAnonymizer(),
    )
    cache_service = DefaultCacheService(cache_repository)
    retrieval_service = DefaultRetrievalService(embedding_provider, vector_query_provider)
    context_assembler = DefaultContextAssembler(context_assembly_policy)
    clinical_reasoning_service = DefaultClinicalReasoningService(
        reasoning_provider,
        reasoning_model_name,
        reasoning_policy,
    )
    clinical_decision_service = DefaultClinicalDecisionService(icd_code_validator)
    persistence_service = DefaultPersistenceService(clinical_decision_repository)

    return AegisContainer(
        clinical_note_repository=clinical_note_repository,
        content_repository=content_repository,
        clinical_decision_repository=clinical_decision_repository,
        clinical_note_service=clinical_note_service,
        normalization_service=normalization_service,
        cache_service=cache_service,
        retrieval_service=retrieval_service,
        context_assembler=context_assembler,
        clinical_reasoning_service=clinical_reasoning_service,
        clinical_decision_service=clinical_decision_service,
        persistence_service=persistence_service,
    )
