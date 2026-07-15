"""
AEGIS workflow graph.

LangGraph orchestration boundary: coordinates execution of the completed
deterministic and probabilistic application services through an explicit
state machine. Owns execution order, the deterministic cache-hit/miss
routing decision, and the interrupt/resume suspension point ahead of
physician review -- never clinical business logic, normalization rules,
retrieval algorithms, context-assembly policy, reasoning, approval
classification, or persistence/cache mechanics, all of which stay owned
by the application services this graph calls.

The full workflow is wired end to end:

    ClinicalNoteSubmission
        -> ClinicalNoteService       (create_clinical_note)
        -> NormalizationService      (normalize_note)
        -> CacheService.lookup       (cache_lookup)

    Cache hit:
        -> END                          (ClinicalDecision already reused)

    Cache miss:
        -> RetrievalService          (retrieve_candidates)
        -> ContextAssembler          (assemble_context)
        -> ClinicalReasoningService  (generate_recommendation)
        -> human_review_pending      (interrupt/resume boundary, no service)
        -> ClinicalDecisionService   (decide_case)
        -> PersistenceService        (persist_clinical_decision)
        -> CacheService.store        (cache_store)
        -> END

``persist_clinical_decision`` is sequenced strictly ahead of
``cache_store`` so that only durably persisted clinical truth ever
becomes reusable cached knowledge -- that ordering is this graph's
responsibility, not either service's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from aegis.graphs.nodes.cache_lookup import make_cache_lookup_node
from aegis.graphs.nodes.cache_store import make_cache_store_node
from aegis.graphs.nodes.clinical_note import make_create_clinical_note_node
from aegis.graphs.nodes.context_assembly import make_assemble_context_node
from aegis.graphs.nodes.decide_case import make_decide_case_node
from aegis.graphs.nodes.generate_recommendation import make_generate_recommendation_node
from aegis.graphs.nodes.human_review import human_review_pending
from aegis.graphs.nodes.normalization import make_normalize_note_node
from aegis.graphs.nodes.persist_clinical_decision import make_persist_clinical_decision_node
from aegis.graphs.nodes.retrieval import make_retrieve_candidates_node
from aegis.graphs.state import AegisWorkflowState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

    from aegis.services.cache_service import CacheService
    from aegis.services.clinical_decision_service import ClinicalDecisionService
    from aegis.services.clinical_note_service import ClinicalNoteService
    from aegis.services.clinical_reasoning_service import ClinicalReasoningService
    from aegis.services.context_assembler import ContextAssembler
    from aegis.services.normalization_service import NormalizationService
    from aegis.services.persistence_service import PersistenceService
    from aegis.services.retrieval_service import RetrievalService


def _route_after_cache_lookup(state: AegisWorkflowState) -> str:
    """Deterministic routing: a cache hit ends the workflow; a miss retrieves evidence."""
    return END if "clinical_decision" in state else "retrieve_candidates"


def build_aegis_graph(
    clinical_note_service: ClinicalNoteService,
    normalization_service: NormalizationService,
    cache_service: CacheService,
    retrieval_service: RetrievalService,
    context_assembler: ContextAssembler,
    clinical_reasoning_service: ClinicalReasoningService,
    clinical_decision_service: ClinicalDecisionService,
    persistence_service: PersistenceService,
    *,
    retrieval_top_k: int,
    retrieval_similarity_threshold: float | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[AegisWorkflowState, Any, AegisWorkflowState, AegisWorkflowState]:
    """
    Compose the full AEGIS workflow graph from injected application services.

    Services are constructed by the caller (FastAPI lifespan, tests, ...)
    and passed in rather than instantiated here, so the graph never binds
    itself to a concrete infrastructure adapter. ``retrieval_top_k`` /
    ``retrieval_similarity_threshold`` are deterministic workflow policy,
    not a ``RetrievalService`` concern, so they are configured here too.

    ``checkpointer`` must be supplied for ``human_review_pending``'s
    interrupt to be resumable -- without one, a cache-miss run raises
    once it reaches that boundary rather than suspending (see
    ``langgraph.types.interrupt``).
    """
    graph: StateGraph[AegisWorkflowState, Any, AegisWorkflowState, AegisWorkflowState] = StateGraph(
        AegisWorkflowState
    )

    graph.add_node("create_clinical_note", make_create_clinical_note_node(clinical_note_service))
    graph.add_node("normalize_note", make_normalize_note_node(normalization_service))
    graph.add_node("cache_lookup", make_cache_lookup_node(cache_service))
    graph.add_node(
        "retrieve_candidates",
        make_retrieve_candidates_node(
            retrieval_service,
            top_k=retrieval_top_k,
            similarity_threshold=retrieval_similarity_threshold,
        ),
    )
    graph.add_node("assemble_context", make_assemble_context_node(context_assembler))
    graph.add_node(
        "generate_recommendation",
        make_generate_recommendation_node(clinical_reasoning_service),
    )
    graph.add_node("human_review_pending", human_review_pending)
    graph.add_node("decide_case", make_decide_case_node(clinical_decision_service))
    graph.add_node(
        "persist_clinical_decision",
        make_persist_clinical_decision_node(persistence_service),
    )
    graph.add_node("cache_store", make_cache_store_node(cache_service))

    graph.add_edge(START, "create_clinical_note")
    graph.add_edge("create_clinical_note", "normalize_note")
    graph.add_edge("normalize_note", "cache_lookup")
    graph.add_conditional_edges("cache_lookup", _route_after_cache_lookup)
    graph.add_edge("retrieve_candidates", "assemble_context")
    graph.add_edge("assemble_context", "generate_recommendation")
    graph.add_edge("generate_recommendation", "human_review_pending")
    graph.add_edge("human_review_pending", "decide_case")
    graph.add_edge("decide_case", "persist_clinical_decision")
    graph.add_edge("persist_clinical_decision", "cache_store")
    graph.add_edge("cache_store", END)

    return graph.compile(checkpointer=checkpointer)
