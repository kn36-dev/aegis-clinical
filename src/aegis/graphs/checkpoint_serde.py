# src/aegis/graphs/checkpoint_serde.py
"""
Explicit checkpoint (de)serialization allow-list for ``AegisWorkflowState``.

LangGraph's ``JsonPlusSerializer`` will, by default, deserialize *any*
Python type found in a checkpoint payload, only warning that unregistered
types will be blocked once ``LANGGRAPH_STRICT_MSGPACK`` is enabled. This
module registers exactly the domain models declared on
``AegisWorkflowState`` (see ``aegis.graphs.state``) so checkpoint
deserialization is explicit today and unaffected when strict mode
eventually becomes the default. See
``docs/tradeoffs_and_limitations.md`` -- "Explicit Workflow Checkpoint
Serialization Registration".

Only ``AegisWorkflowState``'s own domain-artifact fields belong here.
Repositories, services, provider clients, and other infrastructure must
never be registered: checkpoints persist workflow state, not runtime
dependencies.
"""

from __future__ import annotations

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from aegis.models.clinical_decision import ClinicalDecision
from aegis.models.clinical_note import ClinicalNote
from aegis.models.coding_recommendation import CodingRecommendation
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.reasoning_context import ReasoningContext
from aegis.models.retrieval import RetrievalResult
from aegis.models.workflow_commands import ClinicalNoteSubmission, PhysicianDecisionSubmission

ALLOWED_CHECKPOINT_TYPES: tuple[type, ...] = (
    ClinicalNoteSubmission,
    ClinicalNote,
    NormalizedClinicalNote,
    RetrievalResult,
    ReasoningContext,
    CodingRecommendation,
    PhysicianDecisionSubmission,
    ClinicalDecision,
)


def build_checkpoint_serializer() -> JsonPlusSerializer:
    """Serializer restricted to ``AegisWorkflowState``'s domain artifacts."""
    return JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_CHECKPOINT_TYPES)
