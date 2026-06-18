# Spins up AsyncSqliteSaver thread_id
# Hydrates initial graphs/state.py schema

# src/aegis/graphs/workflow.py


from typing import Any

from langgraph.graph import END, StateGraph

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
