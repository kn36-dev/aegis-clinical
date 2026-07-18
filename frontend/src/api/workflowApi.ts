import { httpClient } from "./httpClient";
import type { WorkflowObservabilityResponse } from "../domain/workflow";

/** GET /api/v1/workflows/{workflow_id} — see aegis.api.routers.workflow.get_workflow_observability. */
export function getWorkflowObservability(workflowId: string): Promise<WorkflowObservabilityResponse> {
  return httpClient.get<WorkflowObservabilityResponse>(`/api/v1/workflows/${workflowId}`);
}
