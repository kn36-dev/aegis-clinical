from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_decision import ClinicalDecision, RecommendationDisposition
from aegis.models.coding_recommendation import (
    CodingRecommendation,
    EvidenceReference,
    ICDCodeRecommendation,
    ReasoningMetadata,
)
from aegis.models.workflow_commands import PhysicianDecisionSubmission
from aegis.services.clinical_decision_service import (
    ClinicalDecisionService,
    DefaultClinicalDecisionService,
)


class FakeICDCodeValidator:
    """In-memory stand-in for ``ICDCodeValidator``, used only in tests."""

    def __init__(self, known_codes: set[str] | None = None) -> None:
        self._known_codes = known_codes if known_codes is not None else {"1A00", "1A01", "2B00"}

    def is_valid(self, icd_code: str) -> bool:
        return icd_code in self._known_codes


class FakeIdentifierGenerator:
    def __init__(self, identifier: UUID | None = None) -> None:
        self._identifier = identifier or uuid4()

    def generate(self) -> UUID:
        return self._identifier


class FakeClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now


def make_recommendation(
    case_id: UUID | None = None,
    recommendation_id: UUID | None = None,
    icd_codes: list[str] | None = None,
) -> CodingRecommendation:
    icd_codes = icd_codes if icd_codes is not None else ["1A00"]
    return CodingRecommendation(
        recommendation_id=recommendation_id or uuid4(),
        case_id=case_id or uuid4(),
        recommendations=[
            ICDCodeRecommendation(
                icd_code=code,
                supporting_findings=["watery diarrhea"],
                conflicting_findings=[],
                justification="Findings are consistent with this diagnosis.",
                model_confidence=0.82,
            )
            for code in icd_codes
        ],
        reasoning_summary="Best-supported candidate(s) selected.",
        evidence_reference=EvidenceReference(candidate_icd_codes=icd_codes),
        metadata=ReasoningMetadata(
            model_name="llama-3.3-70b-versatile",
            prompt_version="1.0",
            temperature=0.0,
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )


def make_submission(
    recommendation: CodingRecommendation,
    selected_icd_codes: list[str] | None = None,
    case_id: UUID | None = None,
    recommendation_id: UUID | None = None,
    patient_id_reference: UUID | None = None,
    normalization_version: str = "1.0",
) -> PhysicianDecisionSubmission:
    return PhysicianDecisionSubmission(
        case_id=case_id if case_id is not None else recommendation.case_id,
        recommendation_id=(
            recommendation_id if recommendation_id is not None else recommendation.recommendation_id
        ),
        patient_id_reference=patient_id_reference or uuid4(),
        normalization_version=normalization_version,
        selected_icd_codes=(
            selected_icd_codes
            if selected_icd_codes is not None
            else [r.icd_code for r in recommendation.recommendations]
        ),
    )


@pytest.fixture
def icd_code_validator() -> FakeICDCodeValidator:
    return FakeICDCodeValidator()


@pytest.fixture
def identifier_generator() -> FakeIdentifierGenerator:
    return FakeIdentifierGenerator()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def service(
    icd_code_validator: FakeICDCodeValidator,
    identifier_generator: FakeIdentifierGenerator,
    clock: FakeClock,
) -> DefaultClinicalDecisionService:
    return DefaultClinicalDecisionService(
        icd_code_validator=icd_code_validator,
        identifier_generator=identifier_generator,
        clock=clock,
    )


class TestClinicalDecisionServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            ClinicalDecisionService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(
        self, service: DefaultClinicalDecisionService
    ):
        assert isinstance(service, ClinicalDecisionService)

    def test_service_exposes_only_decide(self):
        public_methods = {
            name for name in vars(ClinicalDecisionService) if not name.startswith("_")
        }
        assert public_methods == {"decide"}


class TestAcceptedRecommendation:
    def test_accepted_code_is_classified_and_preserved(
        self, service: DefaultClinicalDecisionService
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A00"])

        decision = service.decide(recommendation, submission)

        assert isinstance(decision, ClinicalDecision)
        [classification] = decision.approved_icd_codes
        assert classification.icd_code == "1A00"
        assert classification.disposition == RecommendationDisposition.ACCEPTED

    def test_decision_is_immutable(self, service: DefaultClinicalDecisionService):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A00"])

        decision = service.decide(recommendation, submission)

        with pytest.raises(ValidationError):
            decision.normalization_version = "mutated"


class TestRemovedRecommendation:
    def test_ai_suggestion_not_selected_is_excluded_from_approved_codes(
        self, service: DefaultClinicalDecisionService
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=[])

        decision = service.decide(recommendation, submission)

        assert decision.approved_icd_codes == []


class TestAddedRecommendation:
    def test_physician_added_code_not_recommended_by_ai(
        self, service: DefaultClinicalDecisionService
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A00", "2B00"])

        decision = service.decide(recommendation, submission)

        by_code = {c.icd_code: c.disposition for c in decision.approved_icd_codes}
        assert by_code["1A00"] == RecommendationDisposition.ACCEPTED
        assert by_code["2B00"] == RecommendationDisposition.ADDED


class TestModificationIsUnsupported:
    """
    MODIFIED is never inferred: a same-submission removal + addition is
    classified as an independent REMOVED (excluded) + ADDED pair, not
    paired into a MODIFIED disposition, since the physician never
    explicitly declared a replacement (see the service's Modification
    Boundary docstring).
    """

    def test_single_swap_is_not_treated_as_a_modification(
        self, service: DefaultClinicalDecisionService
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A01"])

        decision = service.decide(recommendation, submission)

        [classification] = decision.approved_icd_codes
        assert classification.icd_code == "1A01"
        assert classification.disposition == RecommendationDisposition.ADDED
        assert all(
            c.disposition != RecommendationDisposition.MODIFIED for c in decision.approved_icd_codes
        )

    def test_original_ai_code_is_excluded_not_recorded_as_removed(
        self, service: DefaultClinicalDecisionService
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A01"])

        decision = service.decide(recommendation, submission)

        codes = {c.icd_code for c in decision.approved_icd_codes}
        assert "1A00" not in codes

    def test_multiple_simultaneous_swaps_are_each_independently_added(
        self, service: DefaultClinicalDecisionService, icd_code_validator: FakeICDCodeValidator
    ):
        icd_code_validator._known_codes |= {"1A00", "1A01", "2B00", "2B01"}
        recommendation = make_recommendation(icd_codes=["1A00", "2B00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A01", "2B01"])

        decision = service.decide(recommendation, submission)

        by_code = {c.icd_code: c.disposition for c in decision.approved_icd_codes}
        assert by_code == {
            "1A01": RecommendationDisposition.ADDED,
            "2B01": RecommendationDisposition.ADDED,
        }


class TestInvalidDecision:
    def test_unknown_icd_code_is_rejected(self, service: DefaultClinicalDecisionService):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["9Z99"])

        with pytest.raises(ValueError):
            service.decide(recommendation, submission)

    def test_mismatched_case_id_is_rejected(self, service: DefaultClinicalDecisionService):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, case_id=uuid4())

        with pytest.raises(ValueError):
            service.decide(recommendation, submission)

    def test_mismatched_recommendation_id_is_rejected(
        self, service: DefaultClinicalDecisionService
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, recommendation_id=uuid4())

        with pytest.raises(ValueError):
            service.decide(recommendation, submission)

    def test_duplicate_selected_codes_are_rejected(self, service: DefaultClinicalDecisionService):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A00", "1A00"])

        with pytest.raises(ValueError):
            service.decide(recommendation, submission)


class TestDeterminism:
    def test_same_inputs_produce_identical_decision(
        self,
        icd_code_validator: FakeICDCodeValidator,
        identifier_generator: FakeIdentifierGenerator,
        clock: FakeClock,
    ):
        recommendation = make_recommendation(icd_codes=["1A00"])
        submission = make_submission(recommendation, selected_icd_codes=["1A01"])

        service_a = DefaultClinicalDecisionService(
            icd_code_validator=icd_code_validator,
            identifier_generator=identifier_generator,
            clock=clock,
        )
        service_b = DefaultClinicalDecisionService(
            icd_code_validator=icd_code_validator,
            identifier_generator=identifier_generator,
            clock=clock,
        )

        assert service_a.decide(recommendation, submission) == service_b.decide(
            recommendation, submission
        )


class TestBoundaryProtection:
    def test_service_does_not_mutate_recommendation(self, service: DefaultClinicalDecisionService):
        recommendation = make_recommendation(icd_codes=["1A00"])
        original = recommendation.model_copy(deep=True)
        submission = make_submission(recommendation, selected_icd_codes=["1A00"])

        service.decide(recommendation, submission)

        assert recommendation == original

    def test_service_has_no_persistence_or_retrieval_methods(self):
        public_methods = {
            name for name in vars(DefaultClinicalDecisionService) if not name.startswith("_")
        }
        assert public_methods == {"decide"}
