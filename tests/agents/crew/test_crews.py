from __future__ import annotations

from unittest.mock import MagicMock

from crewai import Process

from aegis.agents.crew.agents import CLINICAL_REASONING_AGENT_ROLE, build_clinical_reasoning_agent
from aegis.agents.crew.crews import build_clinical_reasoning_crew
from aegis.agents.crew.tasks import ICDReasoningOutput, build_icd_reasoning_task


def test_build_clinical_reasoning_agent_is_bound_to_the_given_llm():
    llm = MagicMock()

    agent = build_clinical_reasoning_agent(llm)

    assert agent.role == CLINICAL_REASONING_AGENT_ROLE
    assert agent.llm is llm
    assert agent.allow_delegation is False


def test_build_icd_reasoning_task_wraps_prompt_as_description():
    llm = MagicMock()
    agent = build_clinical_reasoning_agent(llm)

    task = build_icd_reasoning_task(agent, "the rendered reasoning prompt")

    assert task.description == "the rendered reasoning prompt"
    assert task.agent is agent
    assert task.output_pydantic is ICDReasoningOutput


def test_build_clinical_reasoning_crew_assembles_one_agent_and_one_task():
    llm = MagicMock()

    crew = build_clinical_reasoning_crew(llm, "the rendered reasoning prompt")

    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert crew.tasks[0].description == "the rendered reasoning prompt"
    assert crew.process == Process.sequential
