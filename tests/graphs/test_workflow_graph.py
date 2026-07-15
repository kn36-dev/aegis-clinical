"""
Tests for the AEGIS deterministic preparation graph.

Verifies that ``build_aegis_graph`` compiles, that a submission flows
end-to-end to a ``ReasoningContext``, that each node delegates only to
its injected service (never reimplementing service logic or reaching
past its immediate collaborator), that the resulting state carries
domain artifacts only, and that replaying the same input is
deterministic.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from aegis.graphs.state import AegisWorkflowState
from aegis.graphs.workflow import build_aegis_graph
from aegis.models.base import DomainModel
from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.reasoning_context import ReasoningContext
from aegis.models.retrieval import RetrievalCandidate, RetrievalRequest, RetrievalResult
from aegis.services.clinical_note_service import ClinicalNoteService, ClinicalNoteSubmission
from aegis.services.context_assembler import ContextAssembler, DefaultContextAssembler
from aegis.services.normalization_service import NormalizationService
from aegis.services.retrieval_service import RetrievalService

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
FIXED_CASE_ID = UUID("00000000-0000-0000-0000-000000000001")
NORMALIZED_TEXT = "Patient reports no fever. Mild cough."


class FakeClinicalNoteService(ClinicalNoteService):
    """Deterministic test double: always assigns the same case_id."""

    def __init__(self) -> None:
        self.calls: list[ClinicalNoteSubmission] = []

    def create_clinical_note(self, submission: ClinicalNoteSubmission) -> ClinicalNote:
        self.calls.append(submission)
        return ClinicalNote(
            case_id=FIXED_CASE_ID,
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


def make_submission() -> ClinicalNoteSubmission:
    return ClinicalNoteSubmission(
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
    )


@pytest.fixture
def clinical_note_service() -> FakeClinicalNoteService:
    return FakeClinicalNoteService()


@pytest.fixture
def normalization_service() -> FakeNormalizationService:
    return FakeNormalizationService()


@pytest.fixture
def retrieval_service() -> FakeRetrievalService:
    return FakeRetrievalService()


@pytest.fixture
def context_assembler() -> RecordingContextAssembler:
    return RecordingContextAssembler()


@pytest.fixture
def graph(
    clinical_note_service: FakeClinicalNoteService,
    normalization_service: FakeNormalizationService,
    retrieval_service: FakeRetrievalService,
    context_assembler: RecordingContextAssembler,
):
    return build_aegis_graph(
        clinical_note_service,
        normalization_service,
        retrieval_service,
        context_assembler,
        retrieval_top_k=3,
        retrieval_similarity_threshold=0.5,
    )


class TestGraphConstruction:
    def test_graph_compiles(self, graph) -> None:
        assert graph is not None

    def test_graph_contains_only_the_deterministic_preparation_nodes(self, graph) -> None:
        node_names = {name for name in graph.get_graph().nodes if not name.startswith("__")}
        assert node_names == {
            "create_clinical_note",
            "normalize_note",
            "retrieve_candidates",
            "assemble_context",
        }


class TestHappyPath:
    def test_submission_produces_reasoning_context(self, graph) -> None:
        submission = make_submission()

        final_state: AegisWorkflowState = asyncio.run(graph.ainvoke({"submission": submission}))

        assert "reasoning_context" in final_state
        reasoning_context = final_state["reasoning_context"]
        assert isinstance(reasoning_context, ReasoningContext)
        assert reasoning_context.case_id == FIXED_CASE_ID
        assert reasoning_context.anonymized_clinical_text == NORMALIZED_TEXT
        assert [c.icd_code for c in reasoning_context.candidates] == ["1A00"]


class TestNodeIsolation:
    def test_each_node_calls_only_its_own_service_exactly_once(
        self,
        graph,
        clinical_note_service: FakeClinicalNoteService,
        normalization_service: FakeNormalizationService,
        retrieval_service: FakeRetrievalService,
        context_assembler: RecordingContextAssembler,
    ) -> None:
        submission = make_submission()

        asyncio.run(graph.ainvoke({"submission": submission}))

        assert clinical_note_service.calls == [submission]
        assert len(normalization_service.calls) == 1
        assert len(retrieval_service.calls) == 1
        assert retrieval_service.calls[0].top_k == 3
        assert retrieval_service.calls[0].similarity_threshold == 0.5
        assert len(context_assembler.calls) == 1


class TestStateIntegrity:
    def test_final_state_holds_only_declared_domain_artifacts(self, graph) -> None:
        submission = make_submission()

        final_state = asyncio.run(graph.ainvoke({"submission": submission}))

        assert set(final_state.keys()) <= set(AegisWorkflowState.__annotations__)
        for key, value in final_state.items():
            if key == "submission":
                assert isinstance(value, ClinicalNoteSubmission)
            else:
                assert isinstance(value, DomainModel)


class TestDeterministicReplay:
    def test_same_submission_produces_an_equivalent_final_state(
        self,
        clinical_note_service: FakeClinicalNoteService,
        normalization_service: FakeNormalizationService,
        retrieval_service: FakeRetrievalService,
        context_assembler: RecordingContextAssembler,
    ) -> None:
        submission = make_submission()

        graph_one = build_aegis_graph(
            clinical_note_service,
            normalization_service,
            retrieval_service,
            context_assembler,
            retrieval_top_k=3,
        )
        graph_two = build_aegis_graph(
            FakeClinicalNoteService(),
            FakeNormalizationService(),
            FakeRetrievalService(),
            RecordingContextAssembler(),
            retrieval_top_k=3,
        )

        first_run = asyncio.run(graph_one.ainvoke({"submission": submission}))
        second_run = asyncio.run(graph_two.ainvoke({"submission": submission}))

        assert first_run["reasoning_context"] == second_run["reasoning_context"]
        assert first_run["clinical_note"] == second_run["clinical_note"]
        assert first_run["normalized_note"] == second_run["normalized_note"]
