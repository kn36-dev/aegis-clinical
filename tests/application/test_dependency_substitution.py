"""
Dependency substitution: every repository/provider the application
services depend on can be swapped for a fake, with zero SQLite,
Redis, Upstash, or LLM involvement, and the resulting ``AegisContainer``
still produces a fully working LangGraph workflow.

This deliberately bypasses ``build_container`` (which always wires the
three SQLite repositories) to prove the substitutability lives in the
service/container boundary itself, not merely in ``build_container``'s
keyword arguments.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from aegis.application.container import AegisContainer
from aegis.models.workflow_commands import ClinicalNoteSubmission, PhysicianDecisionSubmission
from aegis.services.cache_service import DefaultCacheService
from aegis.services.clinical_decision_service import DefaultClinicalDecisionService
from aegis.services.clinical_note_service import DefaultClinicalNoteService
from aegis.services.clinical_reasoning_service import DefaultClinicalReasoningService
from aegis.services.context_assembler import DefaultContextAssembler
from aegis.services.normalization_service import DefaultNormalizationService
from aegis.services.persistence_service import DefaultPersistenceService
from aegis.services.retrieval_service import DefaultRetrievalService
from tests.application.fakes import (
    KNOWN_ICD_CODE,
    FakeClinicalDecisionCacheRepository,
    FakeClinicalDecisionRepository,
    FakeClinicalNoteRepository,
    FakeContentRepository,
    FakeEmbeddingProvider,
    FakeICDCodeValidator,
    FakePHIAnonymizer,
    FakeReasoningProvider,
    FakeVectorQueryProvider,
    make_submission_kwargs,
)

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from aegis.graphs.state import AegisWorkflowState


def build_fake_container() -> AegisContainer:
    clinical_note_repository = FakeClinicalNoteRepository()
    content_repository = FakeContentRepository()
    clinical_decision_repository = FakeClinicalDecisionRepository()

    return AegisContainer(
        clinical_note_repository=clinical_note_repository,  # type: ignore[arg-type]
        content_repository=content_repository,  # type: ignore[arg-type]
        clinical_decision_repository=clinical_decision_repository,  # type: ignore[arg-type]
        clinical_note_service=DefaultClinicalNoteService(clinical_note_repository),
        normalization_service=DefaultNormalizationService(content_repository, FakePHIAnonymizer()),
        cache_service=DefaultCacheService(FakeClinicalDecisionCacheRepository()),
        retrieval_service=DefaultRetrievalService(
            FakeEmbeddingProvider(), FakeVectorQueryProvider()
        ),
        context_assembler=DefaultContextAssembler(),
        clinical_reasoning_service=DefaultClinicalReasoningService(
            FakeReasoningProvider(), "fake-model"
        ),
        clinical_decision_service=DefaultClinicalDecisionService(FakeICDCodeValidator()),
        persistence_service=DefaultPersistenceService(clinical_decision_repository),
    )


def test_fully_faked_container_runs_the_complete_workflow_to_a_persisted_decision() -> None:
    container = build_fake_container()
    graph = container.build_graph(retrieval_top_k=3, checkpointer=InMemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": str(uuid4())}}
    submission = ClinicalNoteSubmission(**make_submission_kwargs())

    paused_state = asyncio.run(graph.ainvoke({"submission": submission}, config=config))

    assert "__interrupt__" in paused_state
    coding_recommendation = paused_state["coding_recommendation"]
    physician_submission = PhysicianDecisionSubmission(
        case_id=coding_recommendation.case_id,
        recommendation_id=coding_recommendation.recommendation_id,
        patient_id_reference=submission.patient_id,
        normalization_version=paused_state["normalized_note"].normalization_version,
        selected_icd_codes=[KNOWN_ICD_CODE],
    )

    final_state = cast(
        "AegisWorkflowState",
        asyncio.run(graph.ainvoke(Command(resume=physician_submission), config=config)),
    )

    assert "clinical_decision" in final_state
    decision = final_state["clinical_decision"]
    assert decision.decision_id in container.clinical_decision_repository.saved  # type: ignore[attr-defined]
    assert decision.case_id in container.clinical_note_repository.saved  # type: ignore[attr-defined]
