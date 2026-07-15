"""
AEGIS workflow graph.

LangGraph orchestration boundary: coordinates execution of the completed
deterministic application services through an explicit state machine.
Owns execution order and (eventually) resumability and human-in-the-loop
suspension points -- never clinical business logic, normalization
rules, retrieval algorithms, or context-assembly policy, all of which
stay owned by the application services this graph calls.

Only the deterministic preparation pipeline is wired today:

    ClinicalNoteSubmission
        -> ClinicalNoteService     (create_clinical_note)
        -> NormalizationService    (normalize_note)
        -> RetrievalService        (retrieve_candidates)
        -> ContextAssembler        (assemble_context)
        -> ReasoningContext

``ClinicalReasoningService``, ``ClinicalDecisionService``, and
``PersistenceService`` do not exist yet, so this graph intentionally
stops at ``ReasoningContext`` rather than inventing placeholder nodes
for them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from aegis.graphs.nodes.clinical_note import make_create_clinical_note_node
from aegis.graphs.nodes.context_assembly import make_assemble_context_node
from aegis.graphs.nodes.normalization import make_normalize_note_node
from aegis.graphs.nodes.retrieval import make_retrieve_candidates_node
from aegis.graphs.state import AegisWorkflowState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

    from aegis.services.clinical_note_service import ClinicalNoteService
    from aegis.services.context_assembler import ContextAssembler
    from aegis.services.normalization_service import NormalizationService
    from aegis.services.retrieval_service import RetrievalService


def build_aegis_graph(
    clinical_note_service: ClinicalNoteService,
    normalization_service: NormalizationService,
    retrieval_service: RetrievalService,
    context_assembler: ContextAssembler,
    *,
    retrieval_top_k: int,
    retrieval_similarity_threshold: float | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[AegisWorkflowState, Any, AegisWorkflowState, AegisWorkflowState]:
    """
    Compose the deterministic preparation graph from injected application
    services.

    Services are constructed by the caller (FastAPI lifespan, tests, ...)
    and passed in rather than instantiated here, so the graph never binds
    itself to a concrete infrastructure adapter. ``retrieval_top_k`` /
    ``retrieval_similarity_threshold`` are deterministic workflow policy,
    not a ``RetrievalService`` concern, so they are configured here too.
    """
    graph: StateGraph[AegisWorkflowState, Any, AegisWorkflowState, AegisWorkflowState] = (
        StateGraph(AegisWorkflowState)
    )

    graph.add_node("create_clinical_note", make_create_clinical_note_node(clinical_note_service))
    graph.add_node("normalize_note", make_normalize_note_node(normalization_service))
    graph.add_node(
        "retrieve_candidates",
        make_retrieve_candidates_node(
            retrieval_service,
            top_k=retrieval_top_k,
            similarity_threshold=retrieval_similarity_threshold,
        ),
    )
    graph.add_node("assemble_context", make_assemble_context_node(context_assembler))

    graph.add_edge(START, "create_clinical_note")
    graph.add_edge("create_clinical_note", "normalize_note")
    graph.add_edge("normalize_note", "retrieve_candidates")
    graph.add_edge("retrieve_candidates", "assemble_context")
    graph.add_edge("assemble_context", END)

    return graph.compile(checkpointer=checkpointer)
