from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aegis.infrastructure.crewai.reasoning_provider import CrewAIReasoningProvider
from aegis.models.reasoning_context import ReasoningContext

MODULE = "aegis.infrastructure.crewai.reasoning_provider"


def _make_context() -> ReasoningContext:
    return ReasoningContext(
        case_id=uuid4(),
        anonymized_clinical_text="Patient reports no fever. Mild cough.",
        candidates=[],
    )


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_constructor_builds_llm_from_provider_and_model(mock_llm_cls, mock_build_crew):
    CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key", temperature=0.2)

    mock_llm_cls.assert_called_once_with(
        model="groq/qwen/qwen3-32b", api_key="key", temperature=0.2
    )


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_reason_builds_crew_with_llm_and_prompt_then_kicks_off(mock_llm_cls, mock_build_crew):
    mock_llm = MagicMock()
    mock_llm_cls.return_value = mock_llm
    mock_crew = MagicMock()
    mock_build_crew.return_value = mock_crew
    mock_crew.kickoff.return_value = MagicMock(
        pydantic=MagicMock(model_dump=lambda: {"recommendations": [], "reasoning_summary": "ok"}),
        json_dict=None,
        raw="",
    )
    provider = CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key")
    context = _make_context()

    provider.reason(context, "the rendered prompt")

    mock_build_crew.assert_called_once_with(mock_llm, "the rendered prompt")
    mock_crew.kickoff.assert_called_once_with()


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_reason_prefers_pydantic_output(mock_llm_cls, mock_build_crew):
    mock_build_crew.return_value.kickoff.return_value = MagicMock(
        pydantic=MagicMock(
            model_dump=lambda: {"recommendations": [], "reasoning_summary": "from pydantic"}
        ),
        json_dict={"recommendations": [], "reasoning_summary": "from json_dict"},
        raw='{"recommendations": [], "reasoning_summary": "from raw"}',
    )
    provider = CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key")

    result = provider.reason(_make_context(), "prompt")

    assert result == {"recommendations": [], "reasoning_summary": "from pydantic"}


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_reason_falls_back_to_json_dict_when_no_pydantic(mock_llm_cls, mock_build_crew):
    mock_build_crew.return_value.kickoff.return_value = MagicMock(
        pydantic=None,
        json_dict={"recommendations": [], "reasoning_summary": "from json_dict"},
        raw='{"recommendations": [], "reasoning_summary": "from raw"}',
    )
    provider = CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key")

    result = provider.reason(_make_context(), "prompt")

    assert result == {"recommendations": [], "reasoning_summary": "from json_dict"}


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_reason_falls_back_to_parsing_raw_text_as_json(mock_llm_cls, mock_build_crew):
    mock_build_crew.return_value.kickoff.return_value = MagicMock(
        pydantic=None,
        json_dict=None,
        raw='{"recommendations": [], "reasoning_summary": "from raw"}',
    )
    provider = CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key")

    result = provider.reason(_make_context(), "prompt")

    assert result == {"recommendations": [], "reasoning_summary": "from raw"}


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_reason_raises_value_error_when_raw_is_not_valid_json(mock_llm_cls, mock_build_crew):
    mock_build_crew.return_value.kickoff.return_value = MagicMock(
        pydantic=None,
        json_dict=None,
        raw="not json at all",
    )
    provider = CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key")

    with pytest.raises(ValueError, match="no structured output"):
        provider.reason(_make_context(), "prompt")


@patch(f"{MODULE}.build_clinical_reasoning_crew")
@patch(f"{MODULE}.LLM")
def test_reason_raises_value_error_when_raw_json_is_not_an_object(mock_llm_cls, mock_build_crew):
    mock_build_crew.return_value.kickoff.return_value = MagicMock(
        pydantic=None,
        json_dict=None,
        raw="[1, 2, 3]",
    )
    provider = CrewAIReasoningProvider(provider="groq", model="qwen/qwen3-32b", api_key="key")

    with pytest.raises(ValueError, match="non-object JSON"):
        provider.reason(_make_context(), "prompt")
