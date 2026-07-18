import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPendingReviews } from "../../api/reviewApi";
import { ApiError } from "../../api/httpClient";
import type { PendingReviewSummaryResponse } from "../../domain/review";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; cases: PendingReviewSummaryResponse[] };

/** GET /api/v1/reviews — see aegis.api.routers.review.list_pending_reviews. */
export function ReviewQueuePage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    listPendingReviews()
      .then((cases) => {
        if (!cancelled) {
          setState({ kind: "loaded", cases });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message = error instanceof ApiError ? error.detail : "Failed to load review queue.";
        setState({ kind: "error", message });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="review-queue-page">
      <h1>Review Queue</h1>

      {state.kind === "loading" && (
        <p role="status" aria-live="polite">
          Loading pending reviews…
        </p>
      )}

      {state.kind === "error" && (
        <p className="review-page__error" role="alert">
          {state.message}
        </p>
      )}

      {state.kind === "loaded" && state.cases.length === 0 && (
        <p>No cases are currently awaiting physician review.</p>
      )}

      {state.kind === "loaded" && state.cases.length > 0 && (
        <ul className="review-queue-list">
          {state.cases.map((pendingCase) => (
            <li key={pendingCase.workflow_id} className="review-queue-list__item">
              <Link to={`/reviews/${pendingCase.workflow_id}`} className="review-queue-list__link">
                <span className="review-queue-list__case-id">
                  Case <code>{pendingCase.case_id}</code>
                </span>
                <span className="review-queue-list__submitted">
                  Submitted {new Date(pendingCase.submitted_at).toLocaleString()}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
