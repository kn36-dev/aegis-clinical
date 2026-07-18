/**
 * Mirrors aegis.api.schemas.workflow — the DTOs for
 * GET /api/v1/workflows/{workflow_id}.
 */
import type { UUID } from "./common";
import type { ReviewWorkflowStatus } from "./review";

/**
 * One real, completed LangGraph node transition. ``node`` is the actual
 * backend node name (see aegis.graphs.workflow.build_aegis_graph), not a
 * paraphrased label -- presentation labels are applied in this frontend,
 * never invented data.
 */
export interface WorkflowStageResponse {
  node: string;
  completed_at: string;
}

export interface WorkflowObservabilityResponse {
  workflow_id: UUID;
  case_id: UUID;
  status: ReviewWorkflowStatus;
  current_node: string | null;
  stages: WorkflowStageResponse[];
}
