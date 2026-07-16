from __future__ import annotations

from unittest.mock import MagicMock, patch

from crewai import Agent, Process

from aegis.agents.crew.agents import (
    CLINICAL_REASONING_AGENT_BACKSTORY,
    CLINICAL_REASONING_AGENT_GOAL,
    CLINICAL_REASONING_AGENT_ROLE,
    build_clinical_reasoning_agent,
)
from aegis.agents.crew.crews import build_clinical_reasoning_crew
from aegis.agents.crew.tasks import ICDReasoningOutput, build_icd_reasoning_task


def test_build_clinical_reasoning_agent_is_bound_to_the_given_llm():
    llm = MagicMock()

    with patch("aegis.agents.crew.agents.Agent") as mock_agent:
        build_clinical_reasoning_agent(llm)

        mock_agent.assert_called_once_with(
            role=CLINICAL_REASONING_AGENT_ROLE,
            goal=CLINICAL_REASONING_AGENT_GOAL,
            backstory=CLINICAL_REASONING_AGENT_BACKSTORY,
            llm=llm,
            allow_delegation=False,
            verbose=False,
        )


def test_build_icd_reasoning_task_wraps_prompt_as_description():
    agent = Agent(
        role="test-agent",
        goal="test-goal",
        backstory="test-backstory",
    )

    task = build_icd_reasoning_task(agent, "the rendered reasoning prompt")

    assert task.description == "the rendered reasoning prompt"
    assert task.agent is agent
    assert task.output_pydantic is ICDReasoningOutput


def test_build_clinical_reasoning_crew_assembles_one_agent_and_one_task():
    fake_agent = Agent(
        role="test-agent",
        goal="test-goal",
        backstory="test-backstory",
    )

    with patch(
        "aegis.agents.crew.crews.build_clinical_reasoning_agent",
        return_value=fake_agent,
    ):
        crew = build_clinical_reasoning_crew(
            MagicMock(),
            "the rendered reasoning prompt",
        )

    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert crew.tasks[0].description == "the rendered reasoning prompt"
    assert crew.process == Process.sequential
