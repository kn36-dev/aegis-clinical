# Spins up AsyncSqliteSaver thread_id
# Hydrates initial graphs/state.py schema

# src/aegis/graphs/workflow.py


from typing import Any

from langgraph.graph import END, StateGraph

from aegis.database.repository import (
    ClinicalMatchRecord,
    ClinicalRegistryRepository,
    DatabaseManager,
)
from aegis.graphs.state import PatientGraphState


async def anonymize_node(state: PatientGraphState) -> dict[str, Any]:
    # Calls schemas/anonymizer.py logic to clean text strings
    cleaned_text = "Patient [PATIENT_NAME_1] presented with severe symptoms..."
    return {"anonymized_note": cleaned_text, "status": "PENDING_AI"}


async def multi_agent_parsing_node(state: PatientGraphState) -> dict[str, Any]:
    # This node orchestrates CrewAI / PydanticAI processes
    # Returns the structured extractions and confidence metrics

    # Actual logic below
    # validated_data = execute_extraction_crew(state['anonymized_note'])
    # return {
    #     "extracted_codes": validated_data.matches,
    #     "confidence_score": min([m.confidence for m in validated_data.matches]) if validated_data.matches else 0.0
    # }

    return {
        "extracted_codes": [{"code": "1A00", "title": "Cholera"}],
        "confidence_score": 0.78,  # Simulating a lower score to trigger an interrupt
    }


def confidence_routing_edge(state: PatientGraphState) -> str:
    # Deterministic route based on target data validation gates
    if state["confidence_score"] < 0.85:
        return "human_review_wait_state"
    return "auto_archive_state"


async def human_review_node(state: PatientGraphState) -> dict[str, Any]:
    return {"status": "PENDING_HITL"}


async def finalize_archive_node(state: PatientGraphState) -> dict[str, Any]:
    return {"status": "ARCHIVED"}


# Uncompiled so it can be used to test cases
workflow = StateGraph(PatientGraphState)
workflow.add_node("anonymizer", anonymize_node)
workflow.add_node("multi_agent_parser", multi_agent_parsing_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("finalize_archive", finalize_archive_node)

workflow.set_entry_point("anonymizer")
workflow.add_edge("anonymizer", "multi_agent_parser")
workflow.add_conditional_edges(
    "multi_agent_parser",
    confidence_routing_edge,
    {"human_review_wait_state": "human_review", "auto_archive_state": "finalize_archive"},
)
workflow.add_edge("human_review", END)
workflow.add_edge("finalize_archive", END)

# Compile graph with persistence
builder = StateGraph(PatientGraphState)
builder.add_node("anonymizer", anonymize_node)
builder.add_node("multi_agent_parser", multi_agent_parsing_node)
builder.add_node("human_review", human_review_node)
builder.add_node("finalize_archive", finalize_archive_node)

builder.set_entry_point("anonymizer")
builder.add_edge("anonymizer", "multi_agent_parser")
builder.add_conditional_edges(
    "multi_agent_parser",
    confidence_routing_edge,
    {"human_review_wait_state": "human_review", "auto_archive_state": "finalize_archive"},
)
builder.add_edge("human_review", END)
builder.add_edge("finalize_archive", END)

# Compile using compiled checkpointer references passed at the routing tier
compiled_clinical_graph = builder.compile()

# Here is where LangGraph controls the macro-state machine. The Nodes should
# pull the raw payload from the database, hydrate the graph context, and
# execute terminal writes (saving HITL PENDING_REVIEW status and matches)
# Read: use thread_id / patient_id to initialize graph invocation
# Upsert: commit finalized, immutable data to the db

# Global database manager initialized once across the application lifecycle
db_manager = DatabaseManager()


async def anonymize_node(state: PatientGraphState) -> dict[str, Any]:
    """
    Entry point node. Hydrates structural raw text payloads from the core database
    using the provided patient_id, executes scrubbing algorithms, and syncs updates back.
    """
    patient_id = state.get("patient_id")
    if not patient_id:
        raise ValueError("CRITICAL: patient_id missing from initial invocation state context.")

    # 1. READ layer from operational database
    with db_manager.get_connection() as conn:
        repo = ClinicalRegistryRepository(conn)
        record = repo.get_patient_case(patient_id)

    # Fallback to state payload if the database record is being created on-the-fly
    raw_notes = record.raw_notes if record else state.get("raw_notes", "")
    current_version = record.version if record else 1

    # Calls schemas/anonymizer.py logic to clean text strings (Simulated below)
    cleaned_text = "Patient [PATIENT_NAME_1] presented with severe symptoms..."
    new_status = "PENDING_AI"

    # 2. Map updates back to type-safe Pydantic model
    updated_record = ClinicalMatchRecord(
        patient_id=patient_id,
        raw_notes=raw_notes,
        clinical_notes_clear=cleaned_text,
        icd11_codes=[c["code"] for c in state.get("extracted_codes", [])],
        status=new_status,
        version=current_version,
    )

    # 3. UPSERT layer out to SQLite database tracking state transition
    with db_manager.get_connection() as conn:
        repo = ClinicalRegistryRepository(conn)
        repo.upsert_match_results(updated_record)

    return {
        "anonymized_note": cleaned_text,
        "status": new_status,
        "version": current_version + 1,  # Track local state chart version evolution
    }


async def multi_agent_parsing_node(state: PatientGraphState) -> dict[str, Any]:
    """
    Orchestrates specialized parallel CrewAI / PydanticAI worker processes.
    This node remains purely non-deterministic; database state synchronization is delayed
    until routing decisions or interrupts occur.
    """
    # Actual CrewAI worker orchestration execution happens here...
    # validated_data = execute_extraction_crew(state['anonymized_note'])

    return {
        "extracted_codes": [{"code": "1A00", "title": "Cholera"}],
        "confidence_score": 0.78,  # Triggers conditional branch down to HITL
    }


def confidence_routing_edge(state: PatientGraphState) -> str:
    """Deterministic routing decision layer based on validation thresholds."""
    if state["confidence_score"] < 0.85:
        return "human_review_wait_state"
    return "auto_archive_state"


async def human_review_node(state: PatientGraphState) -> dict[str, Any]:
    """
    Terminal Node (Suspended). Commits current extraction matches to the database
    and updates operational visibility to PENDING_HITL for user-dashboard query polling.
    """
    patient_id = state["patient_id"]
    new_status = "PENDING_HITL"

    with db_manager.get_connection() as conn:
        repo = ClinicalRegistryRepository(conn)
        record = repo.get_patient_case(patient_id)

    if record:
        # Extract plain string keys from state format into clean code arrays
        record.icd11_codes = [c["code"] for c in state.get("extracted_codes", [])]
        record.status = new_status
        record.version = state.get("version", record.version)

        with db_manager.get_connection() as conn:
            repo = ClinicalRegistryRepository(conn)
            # Throws a ValueError on version collision (Optimistic Concurrency Control)
            repo.upsert_match_results(record)

    return {"status": new_status}


async def finalize_archive_node(state: PatientGraphState) -> dict[str, Any]:
    """
    Terminal Node (Auto-Archived). Executed when confidence safely hits compliance parameters.
    Saves final configurations completely down to storage.
    """
    patient_id = state["patient_id"]
    new_status = "ARCHIVED"

    with db_manager.get_connection() as conn:
        repo = ClinicalRegistryRepository(conn)
        record = repo.get_patient_case(patient_id)

    if record:
        record.icd11_codes = [c["code"] for c in state.get("extracted_codes", [])]
        record.status = new_status
        record.version = state.get("version", record.version)

        with db_manager.get_connection() as conn:
            repo = ClinicalRegistryRepository(conn)
            repo.upsert_match_results(record)

    return {"status": new_status}
