import { httpClient } from "./httpClient";
import type { WorkflowObservabilityResponse } from "../domain/workflow";

/**
 * GET /api/v1/workflows/{workflow_id} — see aegis.api.routers.workflow.get_workflow_observability.
 *
 * ``includeArtifacts`` requests the raw per-stage artifact payload via
 * ?include_artifacts=true; the backend still only returns it when
 * AppSettings.EXPOSE_WORKFLOW_ARTIFACTS is also enabled server-side, so a
 * `true` here does not guarantee every stage's `artifact` is populated.
 */
export function getWorkflowObservability(
  workflowId: string,
  includeArtifacts = false,
): Promise<WorkflowObservabilityResponse> {
  const query = includeArtifacts ? "?include_artifacts=true" : "";
  return httpClient.get<WorkflowObservabilityResponse>(`/api/v1/workflows/${workflowId}${query}`);
}
