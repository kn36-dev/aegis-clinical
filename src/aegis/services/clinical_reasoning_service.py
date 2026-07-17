"""
ClinicalReasoningService

Implements application_service_contracts/clinical_reasoning_service.md.

Owns the probabilistic reasoning boundary of AEGIS: given a bounded,
deterministic ``ReasoningContext``, produce a structured, advisory
``CodingRecommendation`` through a reasoning process. The reasoning
process itself (CrewAI, a direct LLM call, a deterministic substitute,
or any future framework) is hidden behind the ``ReasoningProvider``
abstraction — replacing it never changes this service's contract.

This module intentionally has no dependency on SQLite, Redis, Upstash
Vector, embedding providers, or LangGraph, and never accesses previous
``ClinicalDecision`` records (see the contract's Historical Decision
Boundary). Prompt text is owned by ``aegis.prompts.icd_reasoning``, not
by this service (see the contract's Prompt Boundary).

``ReasoningProvider`` returns raw, untrusted structured output — this
service owns validating it (schema validation + the "no invented ICD
codes" business invariant) before a ``CodingRecommendation`` is ever
constructed. LLM/model confidence is carried through unchanged as
supplemental information only; it is never treated as clinical truth.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, ValidationError

from aegis.models.base import DomainModel
from aegis.models.coding_recommendation import (
    CodingRecommendation,
    EvidenceReference,
    ICDCodeRecommendation,
    ReasoningMetadata,
)
from aegis.prompts.icd_reasoning import PROMPT_VERSION, build_icd_reasoning_prompt
from aegis.services.clinical_note_service import SystemClock, UUID4IdentifierGenerator

if TYPE_CHECKING:
    from aegis.models.reasoning_context import ReasoningContext
    from aegis.services.clinical_note_service import Clock, IdentifierGenerator

DEFAULT_MAX_ATTEMPTS = 2


class ReasoningProvider(ABC):
    """
    Boundary to the probabilistic reasoning implementation.

    Concrete implementations may invoke CrewAI, a direct LLM call, a
    multi-agent framework, or a deterministic reasoning substitute for
    testing. Whatever the implementation, it returns raw, untrusted
    structured output (parsed JSON, not yet schema-validated) —
    ``ClinicalReasoningService`` owns turning that into a trustworthy
    ``CodingRecommendation`` and never assumes the output is well-formed.
    """

    @abstractmethod
    def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
        """Execute one reasoning pass and return raw structured candidate output."""
        raise NotImplementedError


class _RawICDRecommendation(BaseModel):
    """Untrusted, provider-shaped recommendation prior to validation."""

    icd_code: str
    supporting_findings: list[str] = Field(default_factory=list)
    conflicting_findings: list[str] = Field(default_factory=list)
    justification: str
    model_confidence: float = Field(ge=0.0, le=1.0)


class _RawReasoningOutput(BaseModel):
    """Untrusted, provider-shaped reasoning output prior to validation."""

    recommendations: list[_RawICDRecommendation] = Field(default_factory=list)
    reasoning_summary: str


class ReasoningPolicy(DomainModel):
    """
    Deterministic configuration for reasoning execution.

    ``max_attempts`` bounds how many times ``ReasoningProvider.reason``
    is retried after a validation failure (malformed output or an
    invented ICD code) before the service gives up — the "automatic
    retry" reliability control described by the contract's Structured
    Output Validation section. ``temperature`` is recorded on every
    ``CodingRecommendation`` for reproducibility; this service does not
    interpret it.
    """

    max_attempts: int = Field(gt=0, default=DEFAULT_MAX_ATTEMPTS)
    temperature: float = Field(ge=0.0, default=0.0)


class ClinicalReasoningService(ABC):
    """
    Application service boundary that answers "given this bounded
    clinical evidence, what ICD-11 coding recommendation should be
    proposed?" — never the final clinical truth.

    Performs no retrieval, persistence, workflow routing, or access to
    prior ``ClinicalDecision`` records — see
    application_service_contracts/clinical_reasoning_service.md for the
    full boundary.
    """

    @abstractmethod
    def reason(self, context: ReasoningContext) -> CodingRecommendation:
        """Produce the ``CodingRecommendation`` for this ``ReasoningContext``."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured reasoning model identifier."""
        raise NotImplementedError


class DefaultClinicalReasoningService(ClinicalReasoningService):
    """
    Concrete ``ClinicalReasoningService`` implementation.

    Dependencies are injected so the service remains independently
    testable: a ``ReasoningProvider`` performs the actual (probabilistic)
    reasoning pass; this service owns prompt selection, structured
    output validation, the "no invented ICD codes" invariant, and
    ``CodingRecommendation`` construction.
    """

    def __init__(
        self,
        reasoning_provider: ReasoningProvider,
        model_name: str,
        policy: ReasoningPolicy | None = None,
        identifier_generator: IdentifierGenerator | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._reasoning_provider = reasoning_provider
        self._model_name = model_name
        self._policy = policy or ReasoningPolicy()
        self._identifier_generator = identifier_generator or UUID4IdentifierGenerator()
        self._clock = clock or SystemClock()

    def reason(self, context: ReasoningContext) -> CodingRecommendation:
        prompt = build_icd_reasoning_prompt(context)
        allowed_codes = {candidate.icd_code for candidate in context.candidates}

        last_error: Exception | None = None
        for _ in range(self._policy.max_attempts):
            try:
                raw_output = self._reasoning_provider.reason(context, prompt)
                validated = _RawReasoningOutput.model_validate(raw_output)
                self._validate_codes_are_known(validated, allowed_codes)
                return self._to_coding_recommendation(context, validated)
            except (ValidationError, ValueError) as error:
                last_error = error
                continue

        raise ValueError(
            "Reasoning provider failed to produce a valid CodingRecommendation "
            f"after {self._policy.max_attempts} attempt(s)."
        ) from last_error

    @staticmethod
    def _validate_codes_are_known(validated: _RawReasoningOutput, allowed_codes: set[str]) -> None:
        for recommendation in validated.recommendations:
            if recommendation.icd_code not in allowed_codes:
                raise ValueError(
                    f"Reasoning provider recommended ICD code "
                    f"{recommendation.icd_code!r}, which was not present in the "
                    "supplied ReasoningContext candidates."
                )

    def _to_coding_recommendation(
        self,
        context: ReasoningContext,
        validated: _RawReasoningOutput,
    ) -> CodingRecommendation:
        return CodingRecommendation(
            recommendation_id=self._identifier_generator.generate(),
            case_id=context.case_id,
            recommendations=[
                ICDCodeRecommendation(
                    icd_code=raw.icd_code,
                    supporting_findings=raw.supporting_findings,
                    conflicting_findings=raw.conflicting_findings,
                    justification=raw.justification,
                    model_confidence=raw.model_confidence,
                )
                for raw in validated.recommendations
            ],
            reasoning_summary=validated.reasoning_summary,
            evidence_reference=EvidenceReference(
                candidate_icd_codes=[candidate.icd_code for candidate in context.candidates]
            ),
            metadata=ReasoningMetadata(
                model_name=self._model_name,
                prompt_version=PROMPT_VERSION,
                temperature=self._policy.temperature,
                generated_at=self._clock.now(),
            ),
        )

    @property
    def model_name(self) -> str:
        """Configured reasoning model identifier."""
        return self._model_name
