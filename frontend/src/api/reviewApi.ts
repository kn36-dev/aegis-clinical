import { httpClient } from "./httpClient";
import type {
  PendingReviewSummaryResponse,
  PhysicianDecisionSubmissionRequest,
  ReviewDecisionResponse,
  ReviewStateResponse,
} from "../domain/review";

/** GET /api/v1/reviews — see aegis.api.routers.review.list_pending_reviews. */
export function listPendingReviews(): Promise<PendingReviewSummaryResponse[]> {
  return httpClient.get<PendingReviewSummaryResponse[]>("/api/v1/reviews");
}

/** GET /api/v1/reviews/{thread_id} — see aegis.api.routers.review.get_review_state. */
export function getReviewState(threadId: string): Promise<ReviewStateResponse> {
  return httpClient.get<ReviewStateResponse>(`/api/v1/reviews/${threadId}`);
}

/** POST /api/v1/reviews/{thread_id}/decision — see aegis.api.routers.review.submit_review_decision. */
export function submitReviewDecision(
  threadId: string,
  payload: PhysicianDecisionSubmissionRequest,
): Promise<ReviewDecisionResponse> {
  return httpClient.post<ReviewDecisionResponse>(`/api/v1/reviews/${threadId}/decision`, payload);
}
