"""
Boundary protection: the composition root must hand services
abstractions, never concrete infrastructure objects.

Two independent checks:

1. ``AegisContainer``'s own field annotations name application-service
   abstractions (``ClinicalNoteService``, ...), not concrete
   implementations (``DefaultClinicalNoteService``,
   ``SQLiteClinicalNoteRepository``, ...) -- so holding a container
   reference never leaks which infrastructure backs a capability.
2. The raw ``sqlite3.Connection`` supplied to ``build_container`` is
   confined to the three repository adapters; no application service
   instance holds a reference to it directly.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from aegis.application.container import AegisContainer, build_container
from tests.application.fakes import (
    FakeClinicalDecisionCacheRepository,
    FakeEmbeddingProvider,
    FakeICDCodeValidator,
    FakePHIAnonymizer,
    FakeReasoningProvider,
    FakeVectorQueryProvider,
)

if TYPE_CHECKING:
    import sqlite3


EXPECTED_SERVICE_FIELD_TYPES = {
    "clinical_note_service": "ClinicalNoteService",
    "normalization_service": "NormalizationService",
    "cache_service": "CacheService",
    "retrieval_service": "RetrievalService",
    "context_assembler": "ContextAssembler",
    "clinical_reasoning_service": "ClinicalReasoningService",
    "clinical_decision_service": "ClinicalDecisionService",
    "persistence_service": "PersistenceService",
}


def test_container_fields_are_typed_as_service_abstractions_not_implementations() -> None:
    fields_by_name = {field.name: field for field in dataclasses.fields(AegisContainer)}

    for field_name, expected_type in EXPECTED_SERVICE_FIELD_TYPES.items():
        assert fields_by_name[field_name].type == expected_type


def test_services_never_hold_the_raw_sqlite_connection(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    container = build_container(
        clinical_db_connection,
        cache_repository=FakeClinicalDecisionCacheRepository(),
        embedding_provider=FakeEmbeddingProvider(),
        vector_query_provider=FakeVectorQueryProvider(),
        reasoning_provider=FakeReasoningProvider(),
        reasoning_model_name="test-model",
        icd_code_validator=FakeICDCodeValidator(),
        phi_anonymizer=FakePHIAnonymizer(),
    )

    services = [
        container.clinical_note_service,
        container.normalization_service,
        container.cache_service,
        container.retrieval_service,
        container.context_assembler,
        container.clinical_reasoning_service,
        container.clinical_decision_service,
        container.persistence_service,
    ]

    for service in services:
        for attribute_value in vars(service).values():
            assert attribute_value is not clinical_db_connection, (
                f"{type(service).__name__} holds the raw sqlite3.Connection directly "
                "-- it must depend only on a repository abstraction."
            )
