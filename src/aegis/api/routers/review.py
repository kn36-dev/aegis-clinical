# src/aegis/api/routers/review.py
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends

from aegis.api.dependencies import get_graph_checkpointer
from aegis.graphs.workflow import compiled_clinical_graph

router = APIRouter()

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


@router.post("/approve")
async def approve_hitl_case(
    case_id: str,
    checkpointer: Annotated[Any, Depends(get_graph_checkpointer)],
) -> dict[str, Any]:
    config: RunnableConfig = {"configurable": {"thread_id": case_id}}

    # Hydrate current state snapshot out of the database
    current_state = await compiled_clinical_graph.aget_state(config)

    # Update state properties programmatically
    updated_values = {**current_state.values, "status": "ARCHIVED", "confidence_score": 1.0}
    await compiled_clinical_graph.aupdate_state(config, updated_values, as_node="human_review")

    # Resume execution thread past the pause point
    await compiled_clinical_graph.ainvoke(None, config=config)
    return {"message": f"Case {case_id} successfully approved and archived by physician."}
