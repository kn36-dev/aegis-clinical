"""
AegisWorkflowState

LangGraph runtime state for the AEGIS deterministic preparation graph.

Carries only the immutable domain artifacts produced by the completed
application services along the path
``ClinicalNoteSubmission -> ClinicalNote -> NormalizedClinicalNote ->
RetrievalResult -> ReasoningContext``. LangGraph checkpoints this state
by serializing it, so it must hold domain models only -- never service
instances, repositories, database connections, or LLM clients.

Only ``submission`` is required on entry; every other field is filled in
progressively by the node that produces it.
"""

from __future__ import annotations

from typing import Any, NotRequired, Protocol, TypedDict

# NOT type-checking-only: LangGraph resolves this TypedDict's fields at
# runtime via `typing.get_type_hints()` when the graph is built (see
# StateGraph._add_schema), so these names must exist in this module's
# runtime namespace -- moving them under `if TYPE_CHECKING:` breaks graph
# construction even though ruff's TCH rule would otherwise suggest it.
from aegis.models.clinical_note import ClinicalNote  # noqa: TCH001
from aegis.models.normalized_clinical_note import NormalizedClinicalNote  # noqa: TCH001
from aegis.models.reasoning_context import ReasoningContext  # noqa: TCH001
from aegis.models.retrieval import RetrievalResult  # noqa: TCH001
from aegis.services.clinical_note_service import ClinicalNoteSubmission  # noqa: TCH001


class AegisWorkflowState(TypedDict):
    submission: ClinicalNoteSubmission
    clinical_note: NotRequired[ClinicalNote]
    normalized_note: NotRequired[NormalizedClinicalNote]
    retrieval_result: NotRequired[RetrievalResult]
    reasoning_context: NotRequired[ReasoningContext]


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
