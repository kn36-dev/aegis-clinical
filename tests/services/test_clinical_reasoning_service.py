from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from aegis.models.coding_recommendation import CodingRecommendation
from aegis.models.reasoning_context import CandidateConcept, ReasoningContext
from aegis.services.clinical_reasoning_service import (
    ClinicalReasoningService,
    DefaultClinicalReasoningService,
    ReasoningPolicy,
    ReasoningProvider,
)


class FakeReasoningProvider(ReasoningProvider):
    """In-memory stand-in for ``ReasoningProvider``, used only in tests."""

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self._responses = list(responses) if responses is not None else [_valid_response()]
        self.reason_calls: list[tuple[ReasoningContext, str]] = []

    async def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
        self.reason_calls.append((context, prompt))
        index = min(len(self.reason_calls) - 1, len(self._responses) - 1)
        return self._responses[index]


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


def _valid_response(icd_code: str = "1A00") -> dict[str, Any]:
    return {
        "recommendations": [
            {
                "icd_code": icd_code,
                "supporting_findings": ["watery diarrhea"],
                "conflicting_findings": [],
                "justification": "Findings are consistent with cholera.",
                "model_confidence": 0.82,
            }
        ],
        "reasoning_summary": "Cholera is the best-supported candidate.",
    }


def make_candidate(
    icd_code: str = "1A00",
    title: str = "Cholera",
    hierarchy_context: str | None = "Chapter 1 -> 1A00",
    semantic_representation: str = "Cholera is an acute diarrheal infection.",
) -> CandidateConcept:
    return CandidateConcept(
        icd_code=icd_code,
        title=title,
        hierarchy_context=hierarchy_context,
        semantic_representation=semantic_representation,
    )


def make_context(
    case_id: UUID | None = None,
    anonymized_clinical_text: str = "Patient reports watery diarrhea for two days.",
    candidates: list[CandidateConcept] | None = None,
) -> ReasoningContext:
    return ReasoningContext(
        case_id=case_id or uuid4(),
        anonymized_clinical_text=anonymized_clinical_text,
        candidates=candidates if candidates is not None else [make_candidate()],
    )


@pytest.fixture
def identifier_generator() -> FakeIdentifierGenerator:
    return FakeIdentifierGenerator()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def provider() -> FakeReasoningProvider:
    return FakeReasoningProvider()


@pytest.fixture
def service(
    provider: FakeReasoningProvider,
    identifier_generator: FakeIdentifierGenerator,
    clock: FakeClock,
) -> DefaultClinicalReasoningService:
    return DefaultClinicalReasoningService(
        reasoning_provider=provider,
        model_name="llama-3.3-70b-versatile",
        identifier_generator=identifier_generator,
        clock=clock,
    )


class TestClinicalReasoningServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            ClinicalReasoningService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(
        self, service: DefaultClinicalReasoningService
    ):
        assert isinstance(service, ClinicalReasoningService)

    def test_service_exposes_only_reasoning_boundary_methods(self):
        public_methods = {
            name for name in vars(ClinicalReasoningService) if not name.startswith("_")
        }

        assert public_methods == {"reason", "model_name"}


class TestSuccessfulReasoning:
    async def test_reason_produces_a_coding_recommendation(
        self, service: DefaultClinicalReasoningService
    ):
        recommendation = await service.reason(make_context())

        assert isinstance(recommendation, CodingRecommendation)

    async def test_recommendation_references_the_case_id(
        self, service: DefaultClinicalReasoningService
    ):
        context = make_context()

        recommendation = await service.reason(context)

        assert recommendation.case_id == context.case_id

    async def test_recommendation_carries_the_providers_structured_output(
        self, service: DefaultClinicalReasoningService
    ):
        recommendation = await service.reason(make_context())

        assert len(recommendation.recommendations) == 1
        entry = recommendation.recommendations[0]
        assert entry.icd_code == "1A00"
        assert entry.supporting_findings == ["watery diarrhea"]
        assert entry.conflicting_findings == []
        assert entry.justification == "Findings are consistent with cholera."
        assert entry.model_confidence == 0.82
        assert recommendation.reasoning_summary == "Cholera is the best-supported candidate."

    async def test_recommendation_carries_reproducibility_metadata(
        self, service: DefaultClinicalReasoningService, clock: FakeClock
    ):
        recommendation = await service.reason(make_context())

        assert recommendation.metadata.model_name == "llama-3.3-70b-versatile"
        assert recommendation.metadata.prompt_version
        assert recommendation.metadata.generated_at == clock.now()

    async def test_reason_invokes_provider_with_context_and_a_rendered_prompt(
        self, service: DefaultClinicalReasoningService, provider: FakeReasoningProvider
    ):
        context = make_context()

        await service.reason(context)

        [(called_context, prompt)] = provider.reason_calls
        assert called_context == context
        assert context.anonymized_clinical_text in prompt
        assert context.candidates[0].icd_code in prompt

    async def test_result_is_immutable(self, service: DefaultClinicalReasoningService):
        from pydantic import ValidationError

        recommendation = await service.reason(make_context())

        with pytest.raises(ValidationError):
            recommendation.reasoning_summary = "mutated"


class TestInvalidProviderOutput:
    async def test_malformed_output_is_rejected_after_retries(
        self, identifier_generator: FakeIdentifierGenerator, clock: FakeClock
    ):
        provider = FakeReasoningProvider(responses=[{"not_a_recognized_shape": True}])
        service = DefaultClinicalReasoningService(
            reasoning_provider=provider,
            model_name="llama-3.3-70b-versatile",
            policy=ReasoningPolicy(max_attempts=2),
            identifier_generator=identifier_generator,
            clock=clock,
        )

        with pytest.raises(ValueError):
            await service.reason(make_context())

        assert len(provider.reason_calls) == 2

    async def test_invented_icd_code_is_rejected(
        self, identifier_generator: FakeIdentifierGenerator, clock: FakeClock
    ):
        provider = FakeReasoningProvider(responses=[_valid_response(icd_code="9Z99")])
        service = DefaultClinicalReasoningService(
            reasoning_provider=provider,
            model_name="llama-3.3-70b-versatile",
            policy=ReasoningPolicy(max_attempts=1),
            identifier_generator=identifier_generator,
            clock=clock,
        )

        with pytest.raises(ValueError):
            await service.reason(make_context(candidates=[make_candidate(icd_code="1A00")]))

    async def test_recovers_if_a_later_attempt_succeeds(
        self, identifier_generator: FakeIdentifierGenerator, clock: FakeClock
    ):
        provider = FakeReasoningProvider(
            responses=[{"not_a_recognized_shape": True}, _valid_response()]
        )
        service = DefaultClinicalReasoningService(
            reasoning_provider=provider,
            model_name="llama-3.3-70b-versatile",
            policy=ReasoningPolicy(max_attempts=2),
            identifier_generator=identifier_generator,
            clock=clock,
        )

        recommendation = await service.reason(make_context())

        assert isinstance(recommendation, CodingRecommendation)
        assert len(provider.reason_calls) == 2


class TestProviderReplacement:
    async def test_a_second_reasoning_provider_implementation_satisfies_the_interface(self):
        class AlwaysEmptyReasoningProvider(ReasoningProvider):
            async def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
                return {"recommendations": [], "reasoning_summary": "No candidates matched."}

        service = DefaultClinicalReasoningService(
            reasoning_provider=AlwaysEmptyReasoningProvider(),
            model_name="llama-3.3-70b-versatile",
        )

        recommendation = await service.reason(make_context())

        assert recommendation.recommendations == []
        assert recommendation.reasoning_summary == "No candidates matched."


class TestBoundaryProtection:
    async def test_service_does_not_mutate_reasoning_context(
        self, service: DefaultClinicalReasoningService
    ):
        context = make_context()
        original = context.model_copy(deep=True)

        await service.reason(context)

        assert context == original

    def test_service_has_no_persistence_or_retrieval_methods(self):
        public_methods = {
            name for name in vars(DefaultClinicalReasoningService) if not name.startswith("_")
        }

        assert "reason" in public_methods
        assert "model_name" in public_methods

        forbidden = {
            "save",
            "persist",
            "store",
            "retrieve",
            "lookup",
            "query",
        }

        assert public_methods.isdisjoint(forbidden)
