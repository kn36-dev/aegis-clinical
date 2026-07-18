import type { ReviewWorkflowStatus } from "../../../domain/review";

interface ReviewHeaderProps {
  workflowId: string;
  caseId: string;
  status: ReviewWorkflowStatus;
}

const STATUS_LABEL: Record<ReviewWorkflowStatus, string> = {
  pending_review: "Pending physician review",
  completed: "Review completed",
};

export function ReviewHeader({ workflowId, caseId, status }: ReviewHeaderProps) {
  return (
    <header className="review-header">
      <h1>Physician Review</h1>
      <dl className="review-header__meta">
        <div>
          <dt>Case ID</dt>
          <dd>
            <code>{caseId}</code>
          </dd>
        </div>
        <div>
          <dt>Workflow ID</dt>
          <dd>
            <code>{workflowId}</code>
          </dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>
            <span className={`review-status-pill review-status-pill--${status}`}>
              {STATUS_LABEL[status]}
            </span>
          </dd>
        </div>
      </dl>
    </header>
  );
}
