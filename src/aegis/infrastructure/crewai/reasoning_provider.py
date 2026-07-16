"""
CrewAIReasoningProvider

Concrete ``ReasoningProvider`` (``aegis.services.clinical_reasoning_service``)
backed by CrewAI, with Groq (or any future LiteLLM-supported backend)
as the model transport underneath CrewAI's own LiteLLM integration.

This adapter owns Crew creation, agent execution, task orchestration,
and structured response generation for a single reasoning pass --
nothing else. ``ClinicalReasoningService`` remains the only owner of
schema validation, the "no invented ICD codes" business invariant,
retries, and ``CodingRecommendation`` construction; this adapter
returns raw, untrusted structured output only (a ``dict[str, Any]``),
exactly as ``ReasoningProvider`` requires.

Never accesses SQLite, Redis, repositories, ``RetrievalService``, or
``PersistenceService`` -- it receives only a ``ReasoningContext`` and a
pre-built prompt string (owned by ``aegis.prompts.icd_reasoning``) and
returns a raw dict. Model name, provider, API key, and temperature are
all injected by the caller (the composition root, reading
``AppSettings``) rather than hard-coded here, so swapping Groq for any
other LiteLLM-supported backend is a configuration change only -- see
CLAUDE.md's Provider abstraction and Future Provider Portability.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from crewai import LLM

from aegis.agents.crew.crews import build_clinical_reasoning_crew
from aegis.services.clinical_reasoning_service import ReasoningProvider

if TYPE_CHECKING:
    from aegis.models.reasoning_context import ReasoningContext


class CrewAIReasoningProvider(ReasoningProvider):
    """
    ``ReasoningProvider`` implementation that executes one CrewAI crew
    (a single ``ClinicalReasoningAgent`` running one reasoning ``Task``)
    per ``reason()`` call.

    A fresh ``Crew`` is built for every call rather than reused: a
    ``Task``'s description is the caller-supplied prompt for this one
    ``ReasoningContext``, so there is no cross-call state worth
    preserving between reasoning passes.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        temperature: float = 0.0,
    ) -> None:
        self._llm = LLM(model=f"{provider}/{model}", api_key=api_key, temperature=temperature)

    def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
        crew = build_clinical_reasoning_crew(self._llm, prompt)
        result = crew.kickoff()
        return self._translate(result)

    @staticmethod
    def _translate(result: Any) -> dict[str, Any]:
        """
        Translate a CrewAI ``CrewOutput`` into the raw dict shape
        ``ClinicalReasoningService`` expects, preferring the strongest
        signal CrewAI managed to produce: the validated
        ``ICDReasoningOutput`` pydantic instance, then the parsed JSON
        dict, then a best-effort parse of the raw text. Any of these
        may be untrustworthy (an unconstrained field, a hallucinated
        code) -- that is exactly what ``ClinicalReasoningService``'s own
        validation exists to catch; this method only unwraps CrewAI's
        result shape.
        """
        if result.pydantic is not None:
            return dict(result.pydantic.model_dump())
        if result.json_dict is not None:
            return dict(result.json_dict)

        try:
            parsed = json.loads(result.raw)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"CrewAI reasoning pass produced no structured output: {result.raw!r}"
            ) from error

        if not isinstance(parsed, dict):
            raise ValueError(f"CrewAI reasoning pass produced non-object JSON output: {parsed!r}")

        return parsed
