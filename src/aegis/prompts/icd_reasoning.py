# src/aegis/prompts/icd_reasoning.py
"""
Prompt template for ICD-11 coding recommendation reasoning.

Builds the prompt handed to the reasoning implementation (CrewAI, a
direct LLM call, or any future reasoning framework) from a
``ReasoningContext``. Prompt ownership stays here per the Prompt
Boundary in application_service_contracts/clinical_reasoning_service.md
-- ``ClinicalReasoningService`` selects this template but does not
construct prompt text itself, and this module never decides which
LLM/provider/temperature executes it.

Consumes: ReasoningContext (anonymized_clinical_text + CandidateConcept list)
Produces: ICDSuggestion-shaped structured output (see OUTPUT_SCHEMA)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aegis.prompts.base import build_prompt

if TYPE_CHECKING:
    from aegis.models.reasoning_context import ReasoningContext

PROMPT_VERSION = "1.0"

TASK = (
    "Given the clinical observation and the candidate ICD-11 concepts below, "
    "recommend which candidate ICD-11 codes best classify the observation. "
    "Only recommend codes that appear in the candidate list. For each "
    "recommended code, cite the specific clinical findings that support it "
    "and any findings that conflict with it."
)

OUTPUT_SCHEMA = (
    "{\n"
    '  "recommendations": [\n'
    "    {\n"
    '      "icd_code": string (must be one of the candidate ICD-11 codes below),\n'
    '      "supporting_findings": [string],\n'
    '      "conflicting_findings": [string],\n'
    '      "justification": string,\n'
    '      "model_confidence": float (0.0-1.0)\n'
    "    }\n"
    "  ],\n"
    '  "reasoning_summary": string\n'
    "}"
)


def build_icd_reasoning_prompt(context: ReasoningContext) -> str:
    """Build the reasoning prompt for ``context``."""
    return build_prompt(
        task=TASK,
        input_schema=_render_input(context),
        output_schema=OUTPUT_SCHEMA,
    )


def _render_input(context: ReasoningContext) -> str:
    candidate_lines = "\n".join(
        f"- {candidate.icd_code}: {candidate.title}"
        + (f" ({candidate.hierarchy_context})" if candidate.hierarchy_context else "")
        + f"\n  {candidate.semantic_representation}"
        for candidate in context.candidates
    )
    return (
        f"Clinical observation:\n{context.anonymized_clinical_text}\n\n"
        f"Candidate ICD-11 concepts:\n{candidate_lines or '(none)'}"
    )
