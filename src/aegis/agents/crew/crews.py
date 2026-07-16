"""
CrewAI crew assembly for AEGIS clinical reasoning.

Assembles the single-agent, single-task ``ClinicalReasoningCrew`` used by
``aegis.infrastructure.crewai.reasoning_provider.CrewAIReasoningProvider``.
CrewAI exists solely to execute the reasoning process (see CLAUDE.md's
CrewAI Boundary): this module performs no workflow routing, persistence,
or infrastructure access beyond assembling the ``Crew`` itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from crewai import Crew, Process

from aegis.agents.crew.agents import build_clinical_reasoning_agent
from aegis.agents.crew.tasks import build_icd_reasoning_task

if TYPE_CHECKING:
    from crewai import LLM


def build_clinical_reasoning_crew(llm: LLM, prompt: str) -> Crew:
    """Build the one-shot ``Crew`` that executes a single reasoning pass over ``prompt``."""
    agent = build_clinical_reasoning_agent(llm)
    task = build_icd_reasoning_task(agent, prompt)
    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
