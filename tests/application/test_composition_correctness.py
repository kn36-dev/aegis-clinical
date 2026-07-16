"""
Composition correctness: ``build_container`` must assemble a valid,
fully-typed service graph from real SQLite infrastructure plus the
caller-supplied collaborators that have no production adapter yet.
"""

from __future__ import annotations

import sqlite3

from aegis.application.container import AegisContainer, build_container
from aegis.infrastructure.sqlite.clinical_decision_repository import (
    SQLiteClinicalDecisionRepository,
)
from aegis.infrastructure.sqlite.clinical_note_repository import SQLiteClinicalNoteRepository
from aegis.infrastructure.sqlite.content_store import SQLiteContentStore
from aegis.phi.presidio import PresidioPHIAnonymizer
from aegis.services.cache_service import CacheService
from aegis.services.clinical_decision_service import ClinicalDecisionService
from aegis.services.clinical_note_service import ClinicalNoteService
from aegis.services.clinical_reasoning_service import ClinicalReasoningService
from aegis.services.context_assembler import ContextAssembler
from aegis.services.normalization_service import NormalizationService
from aegis.services.persistence_service import PersistenceService
from aegis.services.retrieval_service import RetrievalService

from tests.application.fakes import (
    FakeClinicalDecisionCacheRepository,
    FakeEmbeddingProvider,
    FakeICDCodeValidator,
    FakePHIAnonymizer,
    FakeReasoningProvider,
    FakeVectorQueryProvider,
)


def _build(connection: sqlite3.Connection, **overrides) -> AegisContainer:
    kwargs = {
        "cache_repository": FakeClinicalDecisionCacheRepository(),
        "embedding_provider": FakeEmbeddingProvider(),
        "vector_query_provider": FakeVectorQueryProvider(),
        "reasoning_provider": FakeReasoningProvider(),
        "reasoning_model_name": "test-model",
        "icd_code_validator": FakeICDCodeValidator(),
        "phi_anonymizer": FakePHIAnonymizer(),
    }
    kwargs.update(overrides)
    return build_container(connection, **kwargs)


class TestRepositoryConstruction:
    def test_constructs_sqlite_repositories_bound_to_the_supplied_connection(
        self, clinical_db_connection: sqlite3.Connection
    ) -> None:
        container = _build(clinical_db_connection)

        assert isinstance(container.clinical_note_repository, SQLiteClinicalNoteRepository)
        assert isinstance(container.content_repository, SQLiteContentStore)
        assert isinstance(container.clinical_decision_repository, SQLiteClinicalDecisionRepository)


class TestServiceConstruction:
    def test_constructs_the_full_service_graph_with_correct_types(
        self, clinical_db_connection: sqlite3.Connection
    ) -> None:
        container = _build(clinical_db_connection)

        assert isinstance(container.clinical_note_service, ClinicalNoteService)
        assert isinstance(container.normalization_service, NormalizationService)
        assert isinstance(container.cache_service, CacheService)
        assert isinstance(container.retrieval_service, RetrievalService)
        assert isinstance(container.context_assembler, ContextAssembler)
        assert isinstance(container.clinical_reasoning_service, ClinicalReasoningService)
        assert isinstance(container.clinical_decision_service, ClinicalDecisionService)
        assert isinstance(container.persistence_service, PersistenceService)

    def test_reasoning_model_name_is_threaded_through(
        self, clinical_db_connection: sqlite3.Connection
    ) -> None:
        container = _build(clinical_db_connection, reasoning_model_name="qwen/qwen3-32b")

        assert container.clinical_reasoning_service._model_name == "qwen/qwen3-32b"  # noqa: SLF001

    def test_defaults_to_the_real_presidio_anonymizer_when_none_is_supplied(
        self, clinical_db_connection: sqlite3.Connection
    ) -> None:
        container = _build(clinical_db_connection, phi_anonymizer=None)

        assert isinstance(
            container.normalization_service._phi_anonymizer,  # noqa: SLF001
            PresidioPHIAnonymizer,
        )


class TestGraphConstruction:
    def test_container_can_build_a_compiled_graph(
        self, clinical_db_connection: sqlite3.Connection
    ) -> None:
        container = _build(clinical_db_connection)

        graph = container.build_graph(retrieval_top_k=3, retrieval_similarity_threshold=0.5)

        node_names = {name for name in graph.get_graph().nodes if not name.startswith("__")}
        assert node_names == {
            "create_clinical_note",
            "normalize_note",
            "cache_lookup",
            "retrieve_candidates",
            "assemble_context",
            "generate_recommendation",
            "human_review_pending",
            "decide_case",
            "persist_clinical_decision",
            "cache_store",
        }
