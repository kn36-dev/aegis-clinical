"""
Integration tests for the full AEGIS workflow graph.

Verifies that ``build_aegis_graph`` wires the cache-hit/cache-miss
routing decision, the deterministic preparation pipeline, the
human-review interrupt/resume boundary, and post-review
persistence-before-cache-store ordering -- coordinating only, with
every node delegating to its injected service and never reimplementing
service logic. Also verifies that graph state never carries anything
beyond the declared domain artifacts.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import aiosqlite
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from aegis.graphs.checkpoint_serde import build_checkpoint_serializer
from aegis.graphs.state import AegisWorkflowState
from aegis.graphs.workflow import build_aegis_graph
from aegis.models.base import DomainModel
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)
from aegis.models.clinical_note import ClinicalNote
from aegis.models.coding_recommendation import (
    CodingRecommendation,
    EvidenceReference,
    ICDCodeRecommendation,
    ReasoningMetadata,
)
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.retrieval import RetrievalCandidate, RetrievalRequest, RetrievalResult
from aegis.models.workflow_commands import ClinicalNoteSubmission, PhysicianDecisionSubmission
from aegis.services.cache_service import CacheService
from aegis.services.clinical_decision_service import ClinicalDecisionService
from aegis.services.clinical_note_service import ClinicalNoteService
from aegis.services.clinical_reasoning_service import ClinicalReasoningService
from aegis.services.context_assembler import ContextAssembler, DefaultContextAssembler
from aegis.services.normalization_service import NormalizationService
from aegis.services.persistence_service import PersistenceResult, PersistenceService
from aegis.services.retrieval_service import RetrievalService

if TYPE_CHECKING:
    from pathlib import Path

    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    from aegis.models.reasoning_context import ReasoningContext

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
FIXED_CASE_ID = UUID("00000000-0000-0000-0000-000000000001")
FIXED_RECOMMENDATION_ID = UUID("00000000-0000-0000-0000-000000000002")
FIXED_DECISION_ID = UUID("00000000-0000-0000-0000-000000000003")
NORMALIZED_TEXT = "Patient reports no fever. Mild cough."

ALL_NODE_NAMES = {
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


class FakeClinicalNoteService(ClinicalNoteService):
    """Deterministic test double: always assigns the same case_id."""

    def __init__(self) -> None:
        self.calls: list[ClinicalNoteSubmission] = []

    def create_clinical_note(
        self, submission: ClinicalNoteSubmission, case_id: UUID | None = None
    ) -> ClinicalNote:
        self.calls.append(submission)
        return ClinicalNote(
            case_id=case_id or FIXED_CASE_ID,
            patient_id=submission.patient_id,
            content_reference=submission.content_reference,
            created_at=FIXED_TIME,
        )


class FakeNormalizationService(NormalizationService):
    def __init__(self) -> None:
        self.calls: list[ClinicalNote] = []

    def normalize(self, clinical_note: ClinicalNote) -> NormalizedClinicalNote:
        self.calls.append(clinical_note)
        return NormalizedClinicalNote(
            clinical_note=clinical_note,
            normalized_text=NORMALIZED_TEXT,
            normalization_version="1.0",
            created_at=FIXED_TIME,
        )

    @property
    def phi_anonymizer(self):
        return self.phi_anonymizer


class FakeCacheService(CacheService):
    """
    Configurable test double: returns ``cached_decision`` on lookup (or
    ``None`` for a miss) and records both lookup and store invocations,
    appending to a shared ``call_order`` so tests can assert ordering
    against ``FakePersistenceService``.
    """

    def __init__(
        self,
        cached_decision: ClinicalDecision | None = None,
        call_order: list[str] | None = None,
    ) -> None:
        self._cached_decision = cached_decision
        self.call_order = call_order if call_order is not None else []
        self.lookup_calls: list[NormalizedClinicalNote] = []
        self.store_calls: list[tuple[NormalizedClinicalNote, ClinicalDecision]] = []

    def lookup(self, normalized_note: NormalizedClinicalNote) -> ClinicalDecision | None:
        self.lookup_calls.append(normalized_note)
        return self._cached_decision

    def store(self, normalized_note: NormalizedClinicalNote, decision: ClinicalDecision) -> None:
        self.store_calls.append((normalized_note, decision))
        self.call_order.append("cache_store")


class FakeRetrievalService(RetrievalService):
    def __init__(self) -> None:
        self.calls: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self.calls.append(request)
        candidate = RetrievalCandidate(
            icd_code="1A00",
            title="Cholera",
            hierarchy_context="Chapter 1 -> 1A00",
            chapter_number="01",
            semantic_representation="Cholera is an acute diarrheal infection.",
            similarity_score=0.91,
            retrieval_metadata={"vector_namespace": "icd11"},
        )
        return RetrievalResult(
            normalized_note=request.normalized_note,
            candidates=[candidate],
            retrieval_metadata={
                "top_k": request.top_k,
                "similarity_threshold": request.similarity_threshold,
            },
        )


class RecordingContextAssembler(ContextAssembler):
    """Wraps the real ``DefaultContextAssembler`` to record call arguments."""

    def __init__(self) -> None:
        self.calls: list[tuple[RetrievalResult, NormalizedClinicalNote]] = []
        self._delegate = DefaultContextAssembler()

    def assemble(
        self,
        retrieval_result: RetrievalResult,
        normalized_note: NormalizedClinicalNote,
    ) -> ReasoningContext:
        self.calls.append((retrieval_result, normalized_note))
        return self._delegate.assemble(retrieval_result, normalized_note)


class FakeClinicalReasoningService(ClinicalReasoningService):
    def __init__(self) -> None:
        self.calls: list[ReasoningContext] = []
        self._model_name = "fake-model"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def reason(self, context: ReasoningContext) -> CodingRecommendation:
        self.calls.append(context)
        return CodingRecommendation(
            recommendation_id=FIXED_RECOMMENDATION_ID,
            case_id=context.case_id,
            recommendations=[
                ICDCodeRecommendation(
                    icd_code="1A00",
                    supporting_findings=["mild cough"],
                    conflicting_findings=[],
                    justification="Consistent with reported findings.",
                    model_confidence=0.8,
                )
            ],
            reasoning_summary="Findings are consistent with cholera.",
            evidence_reference=EvidenceReference(
                candidate_icd_codes=[c.icd_code for c in context.candidates]
            ),
            metadata=ReasoningMetadata(
                model_name="fake-model",
                prompt_version="test",
                temperature=0.0,
                generated_at=FIXED_TIME,
            ),
        )


class FakeClinicalDecisionService(ClinicalDecisionService):
    def __init__(self) -> None:
        self.calls: list[tuple[CodingRecommendation, PhysicianDecisionSubmission]] = []

    def decide(
        self,
        recommendation: CodingRecommendation,
        submission: PhysicianDecisionSubmission,
    ) -> ClinicalDecision:
        self.calls.append((recommendation, submission))
        return ClinicalDecision(
            decision_id=FIXED_DECISION_ID,
            case_id=submission.case_id,
            patient_id_reference=submission.patient_id_reference,
            approved_icd_codes=[
                ApprovedICDClassification(
                    icd_code=code, disposition=RecommendationDisposition.ACCEPTED
                )
                for code in submission.selected_icd_codes
            ],
            normalization_version=submission.normalization_version,
            created_at=FIXED_TIME,
        )


class FakePersistenceService(PersistenceService):
    def __init__(self, call_order: list[str] | None = None) -> None:
        self.call_order = call_order if call_order is not None else []
        self.calls: list[ClinicalDecision] = []

    def persist(self, clinical_decision: ClinicalDecision) -> PersistenceResult:
        self.calls.append(clinical_decision)
        self.call_order.append("persist")
        return PersistenceResult(
            decision_id=clinical_decision.decision_id,
            case_id=clinical_decision.case_id,
            persisted_at=FIXED_TIME,
        )


class FailingPersistenceService(PersistenceService):
    """Always fails, so tests can prove ``cache_store`` never runs afterward."""

    def __init__(self) -> None:
        self.calls: list[ClinicalDecision] = []

    def persist(self, clinical_decision: ClinicalDecision) -> PersistenceResult:
        self.calls.append(clinical_decision)
        raise RuntimeError("storage unavailable")


def make_submission() -> ClinicalNoteSubmission:
    return ClinicalNoteSubmission(
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
    )


def make_config() -> RunnableConfig:
    return {"configurable": {"thread_id": str(uuid4())}}


@pytest.fixture
def clinical_note_service() -> FakeClinicalNoteService:
    return FakeClinicalNoteService()


@pytest.fixture
def normalization_service() -> FakeNormalizationService:
    return FakeNormalizationService()


@pytest.fixture
def call_order() -> list[str]:
    return []


@pytest.fixture
def cache_service(call_order: list[str]) -> FakeCacheService:
    return FakeCacheService(cached_decision=None, call_order=call_order)


@pytest.fixture
def retrieval_service() -> FakeRetrievalService:
    return FakeRetrievalService()


@pytest.fixture
def context_assembler() -> RecordingContextAssembler:
    return RecordingContextAssembler()


@pytest.fixture
def clinical_reasoning_service() -> FakeClinicalReasoningService:
    return FakeClinicalReasoningService()


@pytest.fixture
def clinical_decision_service() -> FakeClinicalDecisionService:
    return FakeClinicalDecisionService()


@pytest.fixture
def persistence_service(call_order: list[str]) -> FakePersistenceService:
    return FakePersistenceService(call_order=call_order)


def build_graph(
    clinical_note_service,
    normalization_service,
    cache_service,
    retrieval_service,
    context_assembler,
    clinical_reasoning_service,
    clinical_decision_service,
    persistence_service,
):
    return build_aegis_graph(
        clinical_note_service,
        normalization_service,
        cache_service,
        retrieval_service,
        context_assembler,
        clinical_reasoning_service,
        clinical_decision_service,
        persistence_service,
        retrieval_top_k=3,
        retrieval_similarity_threshold=0.5,
        checkpointer=InMemorySaver(),
    )


@pytest.fixture
def graph(
    clinical_note_service: FakeClinicalNoteService,
    normalization_service: FakeNormalizationService,
    cache_service: FakeCacheService,
    retrieval_service: FakeRetrievalService,
    context_assembler: RecordingContextAssembler,
    clinical_reasoning_service: FakeClinicalReasoningService,
    clinical_decision_service: FakeClinicalDecisionService,
    persistence_service: FakePersistenceService,
):
    return build_graph(
        clinical_note_service,
        normalization_service,
        cache_service,
        retrieval_service,
        context_assembler,
        clinical_reasoning_service,
        clinical_decision_service,
        persistence_service,
    )


def make_physician_submission(
    coding_recommendation: CodingRecommendation,
    patient_id: UUID,
    normalization_version: str,
) -> PhysicianDecisionSubmission:
    return PhysicianDecisionSubmission(
        case_id=coding_recommendation.case_id,
        recommendation_id=coding_recommendation.recommendation_id,
        patient_id_reference=patient_id,
        normalization_version=normalization_version,
        selected_icd_codes=["1A00"],
    )


class TestGraphConstruction:
    def test_graph_compiles(self, graph) -> None:
        assert graph is not None

    def test_graph_contains_all_workflow_nodes(self, graph) -> None:
        node_names = {name for name in graph.get_graph().nodes if not name.startswith("__")}
        assert node_names == ALL_NODE_NAMES


class TestCacheHit:
    def test_cache_hit_returns_existing_decision_without_downstream_work(
        self,
        clinical_note_service: FakeClinicalNoteService,
        normalization_service: FakeNormalizationService,
        retrieval_service: FakeRetrievalService,
        context_assembler: RecordingContextAssembler,
        clinical_reasoning_service: FakeClinicalReasoningService,
        clinical_decision_service: FakeClinicalDecisionService,
        persistence_service: FakePersistenceService,
        call_order: list[str],
    ) -> None:
        """
        A cached ClinicalDecision is already authoritative clinical truth,
        so a cache hit must bypass RetrievalService, ContextAssembler,
        ClinicalReasoningService, ClinicalDecisionService,
        PersistenceService, and CacheService.store() -- all six,
        completely -- not merely return early while still touching some
        of them.
        """
        cached_decision = ClinicalDecision(
            decision_id=uuid4(),
            case_id=FIXED_CASE_ID,
            patient_id_reference=uuid4(),
            approved_icd_codes=[
                ApprovedICDClassification(
                    icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
                )
            ],
            normalization_version="1.0",
            created_at=FIXED_TIME,
        )
        cache_service = FakeCacheService(cached_decision=cached_decision, call_order=call_order)
        graph = build_graph(
            clinical_note_service,
            normalization_service,
            cache_service,
            retrieval_service,
            context_assembler,
            clinical_reasoning_service,
            clinical_decision_service,
            persistence_service,
        )
        submission = make_submission()

        final_state = cast(
            "AegisWorkflowState",
            asyncio.run(graph.ainvoke({"submission": submission}, config=make_config())),
        )
        assert "clinical_decision" in final_state
        assert final_state["clinical_decision"] == cached_decision
        assert len(cache_service.lookup_calls) == 1

        # A cached ClinicalDecision is already authoritative clinical
        # truth -- a cache hit must bypass every downstream collaborator
        # entirely, not merely skip some of them.
        assert retrieval_service.calls == []  # bypasses RetrievalService
        assert context_assembler.calls == []  # bypasses ContextAssembler
        assert clinical_reasoning_service.calls == []  # bypasses ClinicalReasoningService
        assert clinical_decision_service.calls == []  # bypasses ClinicalDecisionService
        assert persistence_service.calls == []  # bypasses PersistenceService
        assert cache_service.store_calls == []  # bypasses CacheService.store()


class TestCacheMiss:
    def test_cache_miss_executes_retrieval_context_and_reasoning(
        self,
        graph,
        retrieval_service: FakeRetrievalService,
        context_assembler: RecordingContextAssembler,
        clinical_reasoning_service: FakeClinicalReasoningService,
        clinical_decision_service: FakeClinicalDecisionService,
        persistence_service: FakePersistenceService,
        cache_service: FakeCacheService,
    ) -> None:
        submission = make_submission()

        result = asyncio.run(graph.ainvoke({"submission": submission}, config=make_config()))

        assert "__interrupt__" in result
        assert len(retrieval_service.calls) == 1
        assert len(context_assembler.calls) == 1
        assert len(clinical_reasoning_service.calls) == 1
        assert clinical_decision_service.calls == []
        assert persistence_service.calls == []
        assert cache_service.store_calls == []


class TestPersistenceOrdering:
    def test_persistence_happens_before_cache_store(
        self,
        graph,
        clinical_decision_service: FakeClinicalDecisionService,
        persistence_service: FakePersistenceService,
        cache_service: FakeCacheService,
        call_order: list[str],
    ) -> None:
        submission = make_submission()
        config = make_config()

        paused_state = asyncio.run(graph.ainvoke({"submission": submission}, config=config))
        coding_recommendation = paused_state["coding_recommendation"]
        physician_submission = make_physician_submission(
            coding_recommendation,
            patient_id=submission.patient_id,
            normalization_version=paused_state["normalized_note"].normalization_version,
        )

        final_state = asyncio.run(
            graph.ainvoke(Command(resume=physician_submission), config=config)
        )

        assert "clinical_decision" in final_state
        assert len(clinical_decision_service.calls) == 1
        assert call_order == ["persist", "cache_store"]

    def test_ordering_invariant_persist_precedes_cache_store(
        self,
        graph,
        persistence_service: FakePersistenceService,
        cache_service: FakeCacheService,
        call_order: list[str],
    ) -> None:
        """
        Workflow ordering invariant: durable truth must exist before
        deterministic knowledge reuse is updated. PersistenceService.persist()
        must be observed strictly before CacheService.store() -- this test
        asserts that ordering in isolation, independent of any other
        pipeline outcome, so a future change that reorders the graph's
        edges (even if it left every other assertion passing) would be
        caught here specifically.
        """
        submission = make_submission()
        config = make_config()

        paused_state = asyncio.run(graph.ainvoke({"submission": submission}, config=config))
        coding_recommendation = paused_state["coding_recommendation"]
        physician_submission = make_physician_submission(
            coding_recommendation,
            patient_id=submission.patient_id,
            normalization_version=paused_state["normalized_note"].normalization_version,
        )

        asyncio.run(graph.ainvoke(Command(resume=physician_submission), config=config))

        assert persistence_service.calls, "PersistenceService.persist() was never called"
        assert cache_service.store_calls, "CacheService.store() was never called"
        assert call_order.index("persist") < call_order.index("cache_store")

    def test_cache_store_never_runs_if_persistence_fails(
        self,
        clinical_note_service: FakeClinicalNoteService,
        normalization_service: FakeNormalizationService,
        cache_service: FakeCacheService,
        retrieval_service: FakeRetrievalService,
        context_assembler: RecordingContextAssembler,
        clinical_reasoning_service: FakeClinicalReasoningService,
        clinical_decision_service: FakeClinicalDecisionService,
    ) -> None:
        failing_persistence_service = FailingPersistenceService()
        graph = build_graph(
            clinical_note_service,
            normalization_service,
            cache_service,
            retrieval_service,
            context_assembler,
            clinical_reasoning_service,
            clinical_decision_service,
            failing_persistence_service,
        )
        submission = make_submission()
        config = make_config()

        paused_state = asyncio.run(graph.ainvoke({"submission": submission}, config=config))
        coding_recommendation = paused_state["coding_recommendation"]
        physician_submission = make_physician_submission(
            coding_recommendation,
            patient_id=submission.patient_id,
            normalization_version=paused_state["normalized_note"].normalization_version,
        )

        with pytest.raises(RuntimeError, match="storage unavailable"):
            asyncio.run(graph.ainvoke(Command(resume=physician_submission), config=config))

        assert len(failing_persistence_service.calls) == 1
        assert cache_service.store_calls == []


class TestStateIntegrity:
    def test_final_state_holds_only_declared_domain_artifacts(
        self,
        graph,
    ) -> None:
        submission = make_submission()
        config = make_config()

        paused_state = asyncio.run(graph.ainvoke({"submission": submission}, config=config))
        coding_recommendation = paused_state["coding_recommendation"]
        physician_submission = make_physician_submission(
            coding_recommendation,
            patient_id=submission.patient_id,
            normalization_version=paused_state["normalized_note"].normalization_version,
        )

        final_state = asyncio.run(
            graph.ainvoke(Command(resume=physician_submission), config=config)
        )

        assert set(final_state.keys()) <= set(AegisWorkflowState.__annotations__)
        for value in final_state.values():
            assert isinstance(value, DomainModel)


async def _run_pause_then_restore_and_resume(
    db_path: Path,
    serde: JsonPlusSerializer,
    *,
    clinical_note_service: FakeClinicalNoteService,
    normalization_service: FakeNormalizationService,
    cache_service: FakeCacheService,
    retrieval_service: FakeRetrievalService,
    context_assembler: RecordingContextAssembler,
    clinical_reasoning_service: FakeClinicalReasoningService,
    clinical_decision_service: FakeClinicalDecisionService,
    persistence_service: FakePersistenceService,
) -> AegisWorkflowState:
    """
    Drive the workflow through a pause and a resume, reopening the sqlite
    checkpoint file (and a fresh checkpointer/graph instance) in between
    -- proving resume works from a *restored* checkpoint, not merely from
    in-memory graph state that happened to survive.
    """
    submission = make_submission()
    config = make_config()

    def build(checkpointer: AsyncSqliteSaver):
        return build_aegis_graph(
            clinical_note_service,
            normalization_service,
            cache_service,
            retrieval_service,
            context_assembler,
            clinical_reasoning_service,
            clinical_decision_service,
            persistence_service,
            retrieval_top_k=3,
            retrieval_similarity_threshold=0.5,
            checkpointer=checkpointer,
        )

    async with aiosqlite.connect(str(db_path)) as conn:
        saver = AsyncSqliteSaver(conn, serde=serde)
        await saver.setup()
        paused_state = await build(saver).ainvoke({"submission": submission}, config=config)

    assert "__interrupt__" in paused_state

    # Simulate a process restart: a brand-new connection, checkpointer, and
    # compiled graph, all pointed at the same on-disk checkpoint file.
    async with aiosqlite.connect(str(db_path)) as conn:
        saver = AsyncSqliteSaver(conn, serde=serde)
        await saver.setup()
        coding_recommendation = paused_state["coding_recommendation"]
        physician_submission = make_physician_submission(
            coding_recommendation,
            patient_id=submission.patient_id,
            normalization_version=paused_state["normalized_note"].normalization_version,
        )
        final_state = await build(saver).ainvoke(
            Command(resume=physician_submission), config=config
        )

    return cast("AegisWorkflowState", final_state)


class TestCheckpointSerialization:
    """
    Proves the explicit ``allowed_msgpack_modules`` registration in
    ``aegis.graphs.checkpoint_serde`` (see
    ``docs/tradeoffs_and_limitations.md``) actually does its job: the
    real workflow can pause, have its checkpoint written to and restored
    from sqlite, and resume to completion without LangGraph logging an
    "unregistered type" warning for any ``AegisWorkflowState`` domain
    model.
    """

    def test_registered_serializer_round_trips_without_warnings(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        clinical_note_service: FakeClinicalNoteService,
        normalization_service: FakeNormalizationService,
        cache_service: FakeCacheService,
        retrieval_service: FakeRetrievalService,
        context_assembler: RecordingContextAssembler,
        clinical_reasoning_service: FakeClinicalReasoningService,
        clinical_decision_service: FakeClinicalDecisionService,
        persistence_service: FakePersistenceService,
    ) -> None:
        caplog.set_level(logging.WARNING, logger="langgraph.checkpoint.serde.jsonplus")

        final_state = asyncio.run(
            _run_pause_then_restore_and_resume(
                tmp_path / "graph_checkpoints.db",
                build_checkpoint_serializer(),
                clinical_note_service=clinical_note_service,
                normalization_service=normalization_service,
                cache_service=cache_service,
                retrieval_service=retrieval_service,
                context_assembler=context_assembler,
                clinical_reasoning_service=clinical_reasoning_service,
                clinical_decision_service=clinical_decision_service,
                persistence_service=persistence_service,
            )
        )
        for record in caplog.records:
            print(record.name, record.levelname, record.message)

        assert "clinical_decision" in final_state
        assert not any("unregistered type" in record.message for record in caplog.records)
