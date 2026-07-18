import type { WorkflowObservabilityResponse } from "../../domain/workflow";

export type WorkflowObservabilityState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; observability: WorkflowObservabilityResponse };

interface WorkflowStageTimelineProps {
  state: WorkflowObservabilityState;
}

/**
 * Human-readable labels for the real LangGraph node names returned by
 * GET /api/v1/workflows/{workflow_id} (aegis.api.routers.workflow). Purely
 * presentational -- an unrecognized node name (e.g. a future graph change)
 * falls back to rendering its own real name rather than being hidden.
 */
const NODE_LABELS: Record<string, string> = {
  create_clinical_note: "Clinical note received",
  normalize_note: "Note normalized",
  cache_lookup: "Cache checked",
  retrieve_candidates: "ICD-11 retrieval completed",
  assemble_context: "Reasoning context assembled",
  generate_recommendation: "AI recommendation generated",
  human_review_pending: "Physician review",
  decide_case: "Physician decision recorded",
  persist_clinical_decision: "Decision persisted",
  cache_store: "Cache updated",
};

function labelFor(node: string): string {
  return NODE_LABELS[node] ?? node;
}

/**
 * Renders only what GET /api/v1/workflows/{workflow_id} actually reports:
 * one entry per real, completed LangGraph checkpoint transition, each with
 * that checkpoint's own recorded timestamp (see
 * aegis.api.routers.workflow.get_workflow_observability), plus the node
 * LangGraph's own state currently names as next (``current_node``) when
 * the workflow has not yet reached a terminal state. Nothing here
 * estimates a duration, a percentage, or a stage that has not actually
 * completed -- a cache-hit run legitimately renders fewer stages than a
 * cache-miss run. Observability is a secondary, best-effort view: if it
 * fails to load, that is surfaced honestly rather than silently retrying
 * or synthesizing a placeholder timeline.
 */
export function WorkflowStageTimeline({ state }: WorkflowStageTimelineProps) {
  if (state.kind === "loading") {
    return (
      <div className="workflow-stage-timeline">
        <p role="status" aria-live="polite">
          Loading workflow history…
        </p>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="workflow-stage-timeline">
        <p className="workflow-stage-timeline__note">Workflow history unavailable: {state.message}</p>
      </div>
    );
  }

  const { stages, current_node: currentNode } = state.observability;

  return (
    <div className="workflow-stage-timeline">
      <ol className="workflow-stage-timeline__stages" aria-label="Workflow progress">
        {stages.map((stage) => (
          <li
            key={`${stage.node}-${stage.completed_at}`}
            className="workflow-stage-timeline__stage workflow-stage-timeline__stage--complete"
          >
            <span className="workflow-stage-timeline__marker" aria-hidden="true" />
            <span className="workflow-stage-timeline__label">{labelFor(stage.node)}</span>
            <span className="workflow-stage-timeline__timestamp">
              {new Date(stage.completed_at).toLocaleString()}
            </span>
          </li>
        ))}
        {currentNode && (
          <li className="workflow-stage-timeline__stage workflow-stage-timeline__stage--pending">
            <span className="workflow-stage-timeline__marker" aria-hidden="true" />
            <span className="workflow-stage-timeline__label">{labelFor(currentNode)}</span>
          </li>
        )}
      </ol>
    </div>
  );
}
