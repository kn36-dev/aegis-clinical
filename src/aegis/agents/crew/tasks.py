"""
CrewAI task definitions for AEGIS clinical reasoning.

``ICDReasoningOutput`` mirrors the structured shape described by
``aegis.prompts.icd_reasoning.OUTPUT_SCHEMA`` so CrewAI can enforce it
as the task's structured-output contract. This is a provider-internal
schema, distinct from ``ClinicalReasoningService``'s own untrusted-output
validation model (``_RawReasoningOutput``) -- ``ReasoningProvider``
implementations return raw, untrusted ``dict[str, Any]`` output, and
``ClinicalReasoningService`` remains the only place that output becomes
trusted (schema validation + the "no invented ICD codes" invariant).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from crewai import Task
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from crewai import Agent

EXPECTED_OUTPUT = (
    "A JSON object with a 'recommendations' array (each item carrying "
    "icd_code, supporting_findings, conflicting_findings, justification, and "
    "model_confidence) and a 'reasoning_summary' string."
)


class ICDReasoningRecommendation(BaseModel):
    """One structured ICD-11 recommendation, as produced by the reasoning task."""

    icd_code: str
    supporting_findings: list[str] = Field(default_factory=list)
    conflicting_findings: list[str] = Field(default_factory=list)
    justification: str
    model_confidence: float = Field(ge=0.0, le=1.0)


class ICDReasoningOutput(BaseModel):
    """Structured output contract enforced on the CrewAI reasoning task."""

    recommendations: list[ICDReasoningRecommendation] = Field(default_factory=list)
    reasoning_summary: str


def build_icd_reasoning_task(agent: Agent, prompt: str) -> Task:
    """
    Build the single reasoning ``Task`` for one ``ReasoningProvider.reason`` call.

    ``prompt`` is the fully-rendered prompt text produced by
    ``aegis.prompts.icd_reasoning.build_icd_reasoning_prompt`` -- prompt
    ownership stays with the prompt management layer (see the contract's
    Prompt Boundary); this factory only wraps that text as a CrewAI task
    description.
    """
    return Task(
        description=prompt,
        expected_output=EXPECTED_OUTPUT,
        agent=agent,
        output_pydantic=ICDReasoningOutput,
    )
