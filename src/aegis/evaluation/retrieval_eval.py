"""
RetrievalEvaluator

Orchestration-layer harness around the real
``NormalizationService``/``RetrievalService`` boundary:

    ClinicalCase.note
        |
    NormalizationService.normalize  (real PresidioPHIAnonymizer)
        |
    NormalizedClinicalNote
        |
    RetrievalService.retrieve  (real DefaultRetrievalService)
        |
    RetrievalResult
        |
    metrics.compute_case_metrics

Introduces no retrieval, ranking, or normalization logic of its own --
every transformation above is the same real service the production
LangGraph workflow uses, driven here by dataset cases instead of a live
clinical submission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from aegis.evaluation.metrics import CaseMetrics, compute_case_metrics, mean
from aegis.infrastructure.memory.content_repository import FakeContentRepository
from aegis.models.clinical_note import ClinicalNote
from aegis.models.retrieval import RetrievalRequest
from aegis.phi.presidio import PresidioPHIAnonymizer
from aegis.services.normalization_service import DefaultNormalizationService

if TYPE_CHECKING:
    from aegis.evaluation.dataset import ClinicalCase
    from aegis.models.retrieval import RetrievalResult
    from aegis.services.retrieval_service import RetrievalService

# Fixed, non-identifying patient_id for every synthetic evaluation case --
# evaluation cases carry no real patient identity, so a single constant
# (rather than a random uuid4 per run) keeps evaluation runs reproducible.
_EVAL_PATIENT_ID = UUID("00000000-0000-4000-8000-000000000000")
_CASE_ID_NAMESPACE = uuid5(NAMESPACE_URL, "aegis-clinical://evaluation/case")


def _content_reference(case_id: str) -> str:
    return f"eval://{case_id}"


@dataclass(frozen=True)
class RetrievalCaseResult:
    """Per-case retrieval outcome, keyed by the dataset's ``ClinicalCase.id``."""

    case_id: str
    retrieved_codes: list[str]
    relevant_codes: set[str]
    metrics: CaseMetrics


@dataclass(frozen=True)
class RetrievalReport:
    """Aggregate retrieval-evaluation results across the full dataset."""

    case_results: list[RetrievalCaseResult]
    mean_recall_at_k: dict[int, float]
    mean_hit_rate_at_k: dict[int, float]
    mean_mrr: float
    zero_hit_case_ids: list[str]


class RetrievalEvaluator:
    """
    Evaluates ``RetrievalService`` recall/hit-rate/MRR against a dataset
    of ``ClinicalCase`` records.

    Built from real collaborators only: a real ``RetrievalService``
    (local-fixture- or production-backed, per the caller) and a real
    ``NormalizationService`` wired to the real ``PresidioPHIAnonymizer``.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        cases: list[ClinicalCase],
        top_k_values: list[int],
        similarity_threshold: float | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._cases = cases
        self._top_k_values = top_k_values
        self._max_top_k = max(top_k_values)
        self._similarity_threshold = similarity_threshold

        content_by_reference = {_content_reference(case.id): case.note for case in cases}
        self._normalization_service = DefaultNormalizationService(
            content_repository=FakeContentRepository(content_by_reference=content_by_reference),
            phi_anonymizer=PresidioPHIAnonymizer(),
        )

    def _build_clinical_note(self, case: ClinicalCase) -> ClinicalNote:
        return ClinicalNote(
            case_id=uuid5(_CASE_ID_NAMESPACE, case.id),
            patient_id=_EVAL_PATIENT_ID,
            content_reference=_content_reference(case.id),
            created_at=datetime.now(timezone.utc),
        )

    def build_retrieval_result(self, case: ClinicalCase) -> RetrievalResult:
        """
        Run the real normalization + retrieval steps for one case.

        Exposed publicly (not just used internally by ``evaluate_case``) so
        ``ReasoningEvaluator`` can compose it directly instead of
        duplicating clinical-note construction, content seeding, and
        normalization wiring for the reasoning-evaluation boundary
        (``NormalizedClinicalNote + RetrievalResult -> ClinicalReasoningService``).
        """
        clinical_note = self._build_clinical_note(case)
        normalized_note = self._normalization_service.normalize(clinical_note)

        request = RetrievalRequest(
            clinical_note=clinical_note,
            normalized_note=normalized_note,
            top_k=self._max_top_k,
            similarity_threshold=self._similarity_threshold,
        )
        return self._retrieval_service.retrieve(request)

    def evaluate_case(self, case: ClinicalCase) -> RetrievalCaseResult:
        result = self.build_retrieval_result(case)
        retrieved_codes = [candidate.icd_code for candidate in result.candidates]
        relevant_codes = set(case.expected_codes) | set(case.acceptable_codes)

        return RetrievalCaseResult(
            case_id=case.id,
            retrieved_codes=retrieved_codes,
            relevant_codes=relevant_codes,
            metrics=compute_case_metrics(retrieved_codes, relevant_codes, self._top_k_values),
        )

    def evaluate(self) -> RetrievalReport:
        case_results = [self.evaluate_case(case) for case in self._cases]

        mean_recall_at_k = {
            k: mean(result.metrics.recall_at_k[k] for result in case_results)
            for k in self._top_k_values
        }
        mean_hit_rate_at_k = {
            k: mean(result.metrics.hit_rate_at_k[k] for result in case_results)
            for k in self._top_k_values
        }
        mean_mrr = mean(result.metrics.mrr for result in case_results)
        zero_hit_case_ids = [
            result.case_id
            for result in case_results
            if result.metrics.hit_rate_at_k[self._max_top_k] == 0.0
        ]

        return RetrievalReport(
            case_results=case_results,
            mean_recall_at_k=mean_recall_at_k,
            mean_hit_rate_at_k=mean_hit_rate_at_k,
            mean_mrr=mean_mrr,
            zero_hit_case_ids=zero_hit_case_ids,
        )
