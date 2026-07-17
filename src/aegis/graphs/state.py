"""
AegisWorkflowState

LangGraph runtime state for the AEGIS workflow graph.

Carries only the immutable domain artifacts produced by the completed
application services along the path
``ClinicalNoteSubmission -> ClinicalNote -> NormalizedClinicalNote ->
[cache hit: ClinicalDecision] | [cache miss: RetrievalResult ->
ReasoningContext -> CodingRecommendation -> PhysicianDecisionSubmission
-> ClinicalDecision]``. LangGraph checkpoints this state by serializing
it, so it must hold domain models only -- never service instances,
repositories, database connections, or LLM clients.

Only ``submission`` is required on entry; every other field is filled in
progressively by the node that produces it. ``physician_decision_submission``
is the one field not produced by a node's return value in the normal
sense -- it is written externally via ``update_state``/``Command(resume=...)``
when ``human_review_pending`` is resumed (see
``aegis.graphs.nodes.human_review``). It is a transient resume payload,
not an authoritative domain artifact: it exists only to carry physician
input across the interrupt/resume boundary into ``decide_case``, is not
a ``runtime_domain_contracts`` model, and must never be persisted,
cached, or otherwise treated as institutional truth in its own right --
that role belongs solely to the ``ClinicalDecision`` it helps produce.

``case_id`` is an optional entry field, not a domain artifact: it lets a
caller that already knows the canonical workflow identity (the HTTP
ingress layer, which must fix the LangGraph checkpoint ``thread_id``
*before* invoking the graph, ahead of ``create_clinical_note`` ever
running) pass that same identity through to
``ClinicalNoteService.create_clinical_note`` so it becomes
``ClinicalNote.case_id`` too, rather than a second, unrelated id being
minted internally. Callers that omit it are unaffected: the service
falls back to its own ``IdentifierGenerator`` exactly as before.
"""

from __future__ import annotations

from typing import Any, NotRequired, Protocol, TypedDict

# NOT type-checking-only: LangGraph resolves this TypedDict's fields at
# runtime via `typing.get_type_hints()` when the graph is built (see
# StateGraph._add_schema), so these names must exist in this module's
# runtime namespace -- moving them under `if TYPE_CHECKING:` breaks graph
# construction even though ruff's TCH rule would otherwise suggest it.
from uuid import UUID  # noqa: TCH003

from aegis.models.clinical_decision import ClinicalDecision  # noqa: TCH001
from aegis.models.clinical_note import ClinicalNote  # noqa: TCH001
from aegis.models.coding_recommendation import CodingRecommendation  # noqa: TCH001
from aegis.models.normalized_clinical_note import NormalizedClinicalNote  # noqa: TCH001
from aegis.models.reasoning_context import ReasoningContext  # noqa: TCH001
from aegis.models.retrieval import RetrievalResult  # noqa: TCH001
from aegis.models.workflow_commands import (  # noqa: TCH001
    ClinicalNoteSubmission,
    PhysicianDecisionSubmission,
)


class AegisWorkflowState(TypedDict):
    submission: ClinicalNoteSubmission
    case_id: NotRequired[UUID]
    clinical_note: NotRequired[ClinicalNote]
    normalized_note: NotRequired[NormalizedClinicalNote]
    retrieval_result: NotRequired[RetrievalResult]
    reasoning_context: NotRequired[ReasoningContext]
    coding_recommendation: NotRequired[CodingRecommendation]
    physician_decision_submission: NotRequired[PhysicianDecisionSubmission]
    clinical_decision: NotRequired[ClinicalDecision]


class WorkflowNode(Protocol):
    """
    Structural type for a LangGraph node bound to ``AegisWorkflowState``.

    Matches LangGraph's own node-callable shape (a callable named
    ``state``); expressing it as a ``Protocol`` rather than
    ``Callable[[AegisWorkflowState], ...]`` is required for ``add_node``
    to type-check under mypy strict, since plain ``Callable`` types
    cannot satisfy LangGraph's named-parameter node protocol.
    """

    async def __call__(self, state: AegisWorkflowState) -> dict[str, Any]: ...
