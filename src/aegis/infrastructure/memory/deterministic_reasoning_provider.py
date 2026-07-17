"""
DeterministicTopCandidateReasoningProvider

``ReasoningProvider`` (``aegis.services.clinical_reasoning_service``)
adapter for the demo profile: no LLM call, no randomness, no
note-specific branching, and no hardcoded ICD code.

``ClinicalReasoningService`` rejects any recommendation whose
``icd_code`` is not present among the real, already-retrieved
``ReasoningContext.candidates`` -- a fixed/hardcoded code (as a naive
"fake" provider would return) only satisfies that check for whichever
one note happened to retrieve that exact code. Since the demo profile
keeps embedding and Upstash Vector retrieval real (see CLAUDE.md's
demo-profile design), the candidate set genuinely varies per note, so
this provider must read it rather than assume it.

``ReasoningContext.candidates`` is documented (``models/reasoning_context.py``)
as bounded and "in retrieval order" -- selecting ``candidates[0]`` is
therefore selecting the top real semantic match, using only structure
the contract already guarantees, not a similarity score (which
``CandidateConcept`` deliberately does not carry across the reasoning
boundary).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aegis.services.clinical_reasoning_service import ReasoningProvider

if TYPE_CHECKING:
    from aegis.models.reasoning_context import ReasoningContext

_DEMO_MODEL_CONFIDENCE = 0.75


class DeterministicTopCandidateReasoningProvider(ReasoningProvider):
    """
    Deterministic ``ReasoningProvider`` that recommends the top-ranked
    real retrieval candidate from the supplied ``ReasoningContext``.

    Requires at least one candidate; ``ReasoningContext`` construction
    (``ContextAssembler``) is the layer responsible for ensuring that,
    so this provider does not duplicate that check -- it only fails
    loudly, via the existing "no invented ICD codes" retry/error path in
    ``ClinicalReasoningService``, if it somehow receives none.
    """

    def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
        top_candidate = context.candidates[0]
        return {
            "recommendations": [
                {
                    "icd_code": top_candidate.icd_code,
                    "supporting_findings": [
                        f"Highest-ranked semantic match: {top_candidate.title}."
                    ],
                    "conflicting_findings": [],
                    "justification": (
                        "Deterministic demo-profile reasoning: recommendation mirrors the "
                        "top-ranked candidate returned by real semantic retrieval, with no "
                        "LLM reasoning pass performed."
                    ),
                    "model_confidence": _DEMO_MODEL_CONFIDENCE,
                }
            ],
            "reasoning_summary": (
                "Demo profile: this recommendation was derived deterministically from the "
                "top retrieval candidate, not from an LLM reasoning pass."
            ),
        }
