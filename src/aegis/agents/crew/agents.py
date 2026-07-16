"""
CrewAI agent definitions for AEGIS clinical reasoning.

Builds the single ``ClinicalReasoningAgent`` used by
``aegis.infrastructure.crewai.reasoning_provider.CrewAIReasoningProvider``.
Agent construction is a pure factory: no SQLite, Redis, retrieval, or
persistence access happens here or anywhere in ``agents/crew`` (see
CLAUDE.md's CrewAI Boundary). The agent reasons only over the prompt
text it is handed at task-build time -- it never fetches evidence,
prior decisions, or workflow state itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from crewai import Agent

if TYPE_CHECKING:
    from crewai import LLM

CLINICAL_REASONING_AGENT_ROLE = "Clinical Coding Reasoning Specialist"

CLINICAL_REASONING_AGENT_GOAL = (
    "Recommend the ICD-11 codes that best classify the supplied clinical "
    "observation, using only the candidate codes provided -- never inventing "
    "a code outside that candidate set."
)

CLINICAL_REASONING_AGENT_BACKSTORY = (
    "An experienced clinical coding specialist who reasons strictly from the "
    "evidence and candidate concepts explicitly supplied in the task. Never "
    "assumes prior clinical history, prior physician decisions, or "
    "information outside the supplied context."
)


def build_clinical_reasoning_agent(llm: LLM) -> Agent:
    """Build the single-specialist ``ClinicalReasoningAgent`` bound to ``llm``."""
    return Agent(
        role=CLINICAL_REASONING_AGENT_ROLE,
        goal=CLINICAL_REASONING_AGENT_GOAL,
        backstory=CLINICAL_REASONING_AGENT_BACKSTORY,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
