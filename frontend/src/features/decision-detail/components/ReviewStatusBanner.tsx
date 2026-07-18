import type { ReviewWorkflowStatus } from "../../../domain/review";

interface ReviewStatusBannerProps {
  status: ReviewWorkflowStatus;
}

/**
 * Always-visible disclaimer that the AI output below is a suggestion, not a
 * committed clinical decision. Decision submission itself lives in
 * DecisionDetailPage (the submit button below this banner) — this component
 * only renders messaging, never an action.
 */
export function ReviewStatusBanner({ status }: ReviewStatusBannerProps) {
  if (status === "completed") {
    return (
      <div className="review-banner review-banner--completed" role="status">
        This workflow's physician review has already been completed. The decision below is
        recorded; nothing here can be resubmitted from this view.
      </div>
    );
  }

  return (
    <div className="review-banner review-banner--pending" role="status">
      These are AI-generated suggestions only. Physician review is required before any ICD-11
      classification is final — no clinical decision has been committed for this case yet.
    </div>
  );
}
