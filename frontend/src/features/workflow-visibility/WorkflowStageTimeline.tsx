/** The only two states a durable AEGIS workflow can be in, per the actual
 * backend contracts: `ClinicalNoteIngestionResponse.status`
 * (aegis.api.schemas.clinical) and `ReviewStateResponse.status`
 * (aegis.api.schemas.review) share this exact union.
 */
export type DurableWorkflowStatus = "pending_review" | "completed";

interface WorkflowStageTimelineProps {
  status: DurableWorkflowStatus;
}

/**
 * Renders only what the backend actually makes durable and observable today.
 *
 * "Accepted" and "Processing completed" are not independent workflow states —
 * there is no backend signal for "submitted but still processing": the
 * LangGraph workflow runs normalization, ICD-11 retrieval, and AI reasoning
 * synchronously inside a single graph invocation (see
 * aegis.api.routers.clinical._invoke_workflow), so by the time any response
 * exists at all, both of those steps have already happened. They render as
 * complete unconditionally rather than as separately-timestamped stages,
 * because showing them any other way would imply observability the backend
 * doesn't have.
 *
 * The final stage is the one real, durable state: `status`, straight from
 * `ReviewWorkflowStatus`/`WorkflowStatus`. Nothing here polls, animates a
 * duration, or infers a percentage — those would all be fabricated.
 *
 * Per-node progress (e.g. "retrieval complete", "reasoning complete", live
 * status while a workflow is still running) would require the workflow
 * monitoring contract documented but not implemented in
 * src/aegis/api/routers/api_contract_plan.md §5
 * (`GET /api/v1/workflows/{workflow_id}`, current_node/RUNNING/etc.) — see
 * the note this component renders.
 */
export function WorkflowStageTimeline({ status }: WorkflowStageTimelineProps) {
  const reviewStage =
    status === "completed"
      ? { label: "Decision completed", state: "complete" as const }
      : { label: "Human review required", state: "pending" as const };

  return (
    <div className="workflow-stage-timeline">
      <ol className="workflow-stage-timeline__stages" aria-label="Workflow progress">
        <li className="workflow-stage-timeline__stage workflow-stage-timeline__stage--complete">
          <span className="workflow-stage-timeline__marker" aria-hidden="true" />
          <span className="workflow-stage-timeline__label">Accepted</span>
        </li>
        <li className="workflow-stage-timeline__stage workflow-stage-timeline__stage--complete">
          <span className="workflow-stage-timeline__marker" aria-hidden="true" />
          <span className="workflow-stage-timeline__label">Processing completed</span>
        </li>
        <li
          className={`workflow-stage-timeline__stage workflow-stage-timeline__stage--${reviewStage.state}`}
        >
          <span className="workflow-stage-timeline__marker" aria-hidden="true" />
          <span className="workflow-stage-timeline__label">{reviewStage.label}</span>
        </li>
      </ol>
      <p className="workflow-stage-timeline__note">
        Normalization, ICD-11 retrieval, and AI reasoning run as a single synchronous step today,
        so they aren't shown as separate stages here. Granular per-stage progress would require a
        workflow-monitoring API this system doesn't yet expose.
      </p>
    </div>
  );
}
