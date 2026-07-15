from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.reasoning_context import ReasoningContext
from aegis.models.retrieval import RetrievalCandidate, RetrievalResult
from aegis.services.context_assembler import (
    ContextAssembler,
    ContextAssemblyPolicy,
    DefaultContextAssembler,
)


def make_clinical_note(patient_id=None) -> ClinicalNote:
    return ClinicalNote(
        case_id=uuid4(),
        patient_id=patient_id or uuid4(),
        content_reference="content-store://clinical-notes/abc123",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_normalized_note(
    normalized_text: str = "Patient reports no fever. Mild cough.",
    clinical_note: ClinicalNote | None = None,
) -> NormalizedClinicalNote:
    return NormalizedClinicalNote(
        clinical_note=clinical_note or make_clinical_note(),
        normalized_text=normalized_text,
        normalization_version="1.0",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_candidate(
    icd_code: str = "1A00",
    title: str = "Cholera",
    hierarchy_context: str | None = "Chapter 1 -> 1A00",
    semantic_representation: str = "Cholera is an acute diarrheal infection.",
    similarity_score: float = 0.91,
    retrieval_metadata: dict | None = None,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        icd_code=icd_code,
        title=title,
        hierarchy_context=hierarchy_context,
        chapter_number="01",
        semantic_representation=semantic_representation,
        similarity_score=similarity_score,
        retrieval_metadata=retrieval_metadata or {"vector_namespace": "icd11"},
    )


def make_retrieval_result(
    normalized_note: NormalizedClinicalNote | None = None,
    candidates: list[RetrievalCandidate] | None = None,
) -> RetrievalResult:
    note = normalized_note or make_normalized_note()
    return RetrievalResult(
        normalized_note=note,
        candidates=candidates if candidates is not None else [make_candidate()],
        retrieval_metadata={"top_k": 5, "similarity_threshold": None},
    )


@pytest.fixture
def assembler() -> DefaultContextAssembler:
    return DefaultContextAssembler()


class TestContextAssemblerInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            ContextAssembler()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(self, assembler: DefaultContextAssembler):
        assert isinstance(assembler, ContextAssembler)


class TestBasicContextCreation:
    def test_result_is_reasoning_context(self, assembler: DefaultContextAssembler):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert isinstance(context, ReasoningContext)

    def test_case_id_traces_to_source_clinical_note(self, assembler: DefaultContextAssembler):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert context.case_id == note.clinical_note.case_id

    def test_anonymized_text_is_the_normalized_text(self, assembler: DefaultContextAssembler):
        note = make_normalized_note(normalized_text="No fever. Mild cough.")
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert context.anonymized_clinical_text == "No fever. Mild cough."

    def test_candidates_are_translated_into_candidate_concepts(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        candidate = make_candidate(icd_code="1A00", title="Cholera")
        result = make_retrieval_result(normalized_note=note, candidates=[candidate])

        context = assembler.assemble(result, note)

        assert len(context.candidates) == 1
        assert context.candidates[0].icd_code == "1A00"
        assert context.candidates[0].title == "Cholera"
        assert context.candidates[0].hierarchy_context == candidate.hierarchy_context
        assert context.candidates[0].semantic_representation == candidate.semantic_representation

    def test_result_is_immutable(self, assembler: DefaultContextAssembler):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        with pytest.raises(ValidationError):
            context.anonymized_clinical_text = "mutated"

    def test_rejects_retrieval_result_from_a_different_normalized_note(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        other_note = make_normalized_note(normalized_text="A different observation.")
        result = make_retrieval_result(normalized_note=other_note)

        with pytest.raises(ValueError):
            assembler.assemble(result, note)


class TestDeterminism:
    def test_same_inputs_produce_identical_output(self):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        first = DefaultContextAssembler().assemble(result, note)
        second = DefaultContextAssembler().assemble(result, note)

        assert first == second

    def test_is_deterministic_across_repeated_calls_on_same_instance(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        assert assembler.assemble(result, note) == assembler.assemble(result, note)


class TestCandidateBounding:
    def test_excess_candidates_are_truncated_to_policy_limit(self):
        note = make_normalized_note()
        candidates = [make_candidate(icd_code=f"1A0{i}") for i in range(5)]
        result = make_retrieval_result(normalized_note=note, candidates=candidates)
        assembler = DefaultContextAssembler(policy=ContextAssemblyPolicy(max_candidates=2))

        context = assembler.assemble(result, note)

        assert len(context.candidates) == 2

    def test_bounding_preserves_retrieval_order(self):
        note = make_normalized_note()
        candidates = [
            make_candidate(icd_code="1A00"),
            make_candidate(icd_code="1A01"),
            make_candidate(icd_code="1A02"),
        ]
        result = make_retrieval_result(normalized_note=note, candidates=candidates)
        assembler = DefaultContextAssembler(policy=ContextAssemblyPolicy(max_candidates=2))

        context = assembler.assemble(result, note)

        assert [c.icd_code for c in context.candidates] == ["1A00", "1A01"]

    def test_default_policy_bounds_to_default_max_candidates(self):
        note = make_normalized_note()
        candidates = [make_candidate(icd_code=f"1A0{i}") for i in range(10)]
        result = make_retrieval_result(normalized_note=note, candidates=candidates)
        assembler = DefaultContextAssembler()

        context = assembler.assemble(result, note)

        assert len(context.candidates) == ContextAssemblyPolicy().max_candidates


class TestDuplicateHandling:
    def test_duplicate_icd_codes_are_collapsed_to_one_candidate(self):
        # RetrievalResult itself enforces no duplicate ICD codes (see
        # below), so this exercises the assembler's own defensive
        # dedup directly rather than relying on that upstream
        # invariant holding.
        duplicate = make_candidate(icd_code="1A00", title="Cholera")
        assembler = DefaultContextAssembler()

        deduped = assembler._select_candidates([duplicate, duplicate])

        assert len(deduped) == 1
        assert deduped[0].icd_code == "1A00"

    def test_retrieval_result_itself_rejects_duplicate_icd_codes(self):
        note = make_normalized_note()

        with pytest.raises(ValidationError):
            make_retrieval_result(
                normalized_note=note,
                candidates=[make_candidate(icd_code="1A00"), make_candidate(icd_code="1A00")],
            )


class TestBoundaryEnforcement:
    def test_no_similarity_score_field_on_candidate_concept(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert not hasattr(context.candidates[0], "similarity_score")

    def test_no_retrieval_metadata_field_on_candidate_concept(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert not hasattr(context.candidates[0], "retrieval_metadata")

    def test_no_patient_id_field_on_reasoning_context(self, assembler: DefaultContextAssembler):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert not hasattr(context, "patient_id")
        assert "patient_id" not in context.model_dump()

    def test_no_clinical_note_or_normalized_note_embedded_on_reasoning_context(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert not hasattr(context, "clinical_note")
        assert not hasattr(context, "normalized_note")

    def test_patient_id_does_not_leak_via_serialization(self, assembler: DefaultContextAssembler):
        patient_id = uuid4()
        note = make_normalized_note(clinical_note=make_clinical_note(patient_id=patient_id))
        result = make_retrieval_result(normalized_note=note)

        context = assembler.assemble(result, note)

        assert str(patient_id) not in context.model_dump_json()


class TestEmptyRetrievalBehavior:
    def test_no_candidates_produces_empty_candidate_list(self, assembler: DefaultContextAssembler):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note, candidates=[])

        context = assembler.assemble(result, note)

        assert context.candidates == []

    def test_no_candidates_still_produces_valid_reasoning_context(
        self, assembler: DefaultContextAssembler
    ):
        note = make_normalized_note()
        result = make_retrieval_result(normalized_note=note, candidates=[])

        context = assembler.assemble(result, note)

        assert isinstance(context, ReasoningContext)
        assert context.case_id == note.clinical_note.case_id
