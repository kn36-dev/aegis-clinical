"""
ReasoningEvaluator

Orchestration-layer harness around the real
``ContextAssembler``/``ClinicalReasoningService`` boundary:

    NormalizedClinicalNote + RetrievalResult   (from RetrievalEvaluator)
        |
    ContextAssembler.assemble  (real DefaultContextAssembler)
        |
    ReasoningContext
        |
    ClinicalReasoningService.reason  (real DefaultClinicalReasoningService)
        |
    CodingRecommendation
        |
    deterministic scoring against ClinicalCase.expected_codes/acceptable_codes

Introduces no reasoning, ranking, or context-assembly logic of its own --
retrieval evidence comes from a real ``RetrievalEvaluator`` (never a
fabricated ``ReasoningContext``), and scoring is pure set-membership /
non-emptiness checks. No LLM-as-judge.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import ValidationError

if TYPE_CHECKING:
    from aegis.evaluation.dataset import ClinicalCase
    from aegis.evaluation.retrieval_eval import RetrievalEvaluator
    from aegis.services.clinical_reasoning_service import ClinicalReasoningService
    from aegis.services.context_assembler import ContextAssembler


class ExpectedCodeAlignment(StrEnum):
    """
    How a ``CodingRecommendation``'s recommended codes relate to a case's
    ground-truth annotations.

    Deliberately neutral naming: a ``MISALIGNED`` result means the
    recommendation disagreed with this case's annotations, not that the
    model "hallucinated" or produced an "unsupported" code --
    ``ClinicalReasoningService`` already structurally guarantees every
    recommended code was among the retrieved candidates (see its "no
    invented ICD codes" invariant); this axis measures annotation
    agreement, a separate and softer question.
    """

    EXPECTED = "expected"
    ACCEPTABLE = "acceptable"
    MISALIGNED = "misaligned"


@dataclass(frozen=True)
class ReasoningCaseResult:
    """Per-case reasoning outcome, keyed by the dataset's ``ClinicalCase.id``."""

    case_id: str
    schema_valid: bool
    expected_code_alignment: ExpectedCodeAlignment | None
    evidence_grounded: bool | None
    recommended_codes: list[str]
    error: str | None


@dataclass(frozen=True)
class ReasoningReport:
    """Aggregate reasoning-evaluation results across the full dataset."""

    case_results: list[ReasoningCaseResult]
    schema_valid_rate: float
    expected_alignment_rate: float
    acceptable_or_better_alignment_rate: float
    evidence_grounded_rate: float
    misaligned_case_ids: list[str]
    failed_case_ids: list[str]


class ReasoningEvaluator:
    """
    Evaluates ``ClinicalReasoningService`` output against a dataset of
    ``ClinicalCase`` records.

    Built from real collaborators only: a real ``ContextAssembler``, a
    real ``ClinicalReasoningService`` (optionally rate-limited -- see
    ``rate_limiter.RateLimitedReasoningProvider`` -- but never a
    different reasoning implementation), and a ``RetrievalEvaluator`` that
    supplies real retrieval evidence per case.
    """

    def __init__(
        self,
        retrieval_evaluator: RetrievalEvaluator,
        context_assembler: ContextAssembler,
        reasoning_service: ClinicalReasoningService,
    ) -> None:
        self._retrieval_evaluator = retrieval_evaluator
        self._context_assembler = context_assembler
        self._reasoning_service = reasoning_service

    async def evaluate_case(self, case: ClinicalCase) -> ReasoningCaseResult:
        retrieval_result = self._retrieval_evaluator.build_retrieval_result(case)

        try:
            context = self._context_assembler.assemble(
                retrieval_result, retrieval_result.normalized_note
            )
            recommendation = await self._reasoning_service.reason(context)
        except (ValidationError, ValueError) as error:
            return ReasoningCaseResult(
                case_id=case.id,
                schema_valid=False,
                expected_code_alignment=None,
                evidence_grounded=None,
                recommended_codes=[],
                error=str(error),
            )

        recommended_codes = [item.icd_code for item in recommendation.recommendations]
        recommended_code_set = set(recommended_codes)
        expected_codes = set(case.expected_codes)
        acceptable_codes = set(case.acceptable_codes)

        if recommended_code_set & expected_codes:
            alignment = ExpectedCodeAlignment.EXPECTED
        elif recommended_code_set & acceptable_codes:
            alignment = ExpectedCodeAlignment.ACCEPTABLE
        else:
            alignment = ExpectedCodeAlignment.MISALIGNED

        evidence_grounded = all(
            item.supporting_findings and item.justification.strip()
            for item in recommendation.recommendations
        )

        return ReasoningCaseResult(
            case_id=case.id,
            schema_valid=True,
            expected_code_alignment=alignment,
            evidence_grounded=evidence_grounded,
            recommended_codes=recommended_codes,
            error=None,
        )

    async def evaluate(self, cases: list[ClinicalCase]) -> ReasoningReport:
        case_results = [await self.evaluate_case(case) for case in cases]
        total = len(case_results) or 1

        valid_results = [result for result in case_results if result.schema_valid]
        expected_hits = sum(
            1
            for result in valid_results
            if result.expected_code_alignment is ExpectedCodeAlignment.EXPECTED
        )
        acceptable_or_better_hits = sum(
            1
            for result in valid_results
            if result.expected_code_alignment
            in (ExpectedCodeAlignment.EXPECTED, ExpectedCodeAlignment.ACCEPTABLE)
        )
        grounded_hits = sum(1 for result in valid_results if result.evidence_grounded)

        return ReasoningReport(
            case_results=case_results,
            schema_valid_rate=len(valid_results) / total,
            expected_alignment_rate=expected_hits / total,
            acceptable_or_better_alignment_rate=acceptable_or_better_hits / total,
            evidence_grounded_rate=grounded_hits / total,
            misaligned_case_ids=[
                result.case_id
                for result in valid_results
                if result.expected_code_alignment is ExpectedCodeAlignment.MISALIGNED
            ],
            failed_case_ids=[result.case_id for result in case_results if not result.schema_valid],
        )
