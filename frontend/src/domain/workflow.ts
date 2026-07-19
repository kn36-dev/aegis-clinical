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
/**
 * Raw domain artifact produced by one completed workflow stage. ``payload``
 * is the corresponding domain model's own serialized output (see
 * aegis.api.schemas.workflow.WorkflowStageArtifact) -- rendered exactly as
 * the backend produced it, never interpreted or reshaped here.
 */
export interface WorkflowStageArtifact {
  artifact_type: string;
  payload: Record<string, unknown>;
}

export interface WorkflowStageResponse {
  node: string;
  completed_at: string;
  artifact?: WorkflowStageArtifact | null;
}

export interface WorkflowObservabilityResponse {
  workflow_id: UUID;
  case_id: UUID;
  status: ReviewWorkflowStatus;
  current_node: string | null;
  stages: WorkflowStageResponse[];
}
