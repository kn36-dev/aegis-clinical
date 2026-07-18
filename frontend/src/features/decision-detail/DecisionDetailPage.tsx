import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../../api/httpClient";
import { getReviewState, submitReviewDecision } from "../../api/reviewApi";
import type { ICDCode } from "../../domain/common";
import type { ReviewStateResponse } from "../../domain/review";
import { ClinicalContextCard } from "./components/ClinicalContextCard";
import { RecommendationList } from "./components/RecommendationList";
import { ReviewHeader } from "./components/ReviewHeader";
import { ReviewStatusBanner } from "./components/ReviewStatusBanner";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; review: ReviewStateResponse };

type SubmitState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; decisionId: string }
  | { kind: "error"; message: string };

/**
 * GET/POST /api/v1/reviews/{thread_id}... — see
 * aegis.api.routers.review.get_review_state/submit_review_decision.
 */
export function DecisionDetailPage() {
  // React Router exposes this as threadId because LangGraph calls its
  // persisted execution identifier a thread ID. The application/API layer
  // calls the same identifier workflow_id, so rename it at this boundary.
  const { threadId: workflowId } = useParams<{ threadId: string }>();

  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });
  // Tracks deviations from "every recommendation approved" rather than the
  // selection itself, so this can start empty and not depend on the review
  // data that only arrives after the fetch below resolves.
  const [deselectedIcdCodes, setDeselectedIcdCodes] = useState<Set<ICDCode>>(() => new Set());

  useEffect(() => {
    if (!workflowId) {
      return;
    }

    let cancelled = false;

    getReviewState(workflowId)
      .then((review) => {
        if (!cancelled) {
          setState({ kind: "loaded", review });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        const message =
          error instanceof ApiError
            ? error.status === 404
              ? `No workflow found for id ${workflowId}.`
              : error.detail
            : "Failed to load review.";

        setState({ kind: "error", message });
      });

    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  if (!workflowId) {
    return (
      <section className="review-page">
        <p className="review-page__error">
          No workflow id was provided in the URL.
        </p>
      </section>
    );
  }

  if (state.kind === "loading") {
    return (
      <section className="review-page">
        <p>Loading review…</p>
      </section>
    );
  }

  if (state.kind === "error") {
    return (
      <section className="review-page">
        <p className="review-page__error">{state.message}</p>
      </section>
    );
  }

  const { review } = state;
  const isPendingReview = review.status === "pending_review";
  const selectedIcdCodes = new Set(
    (review.recommended_icd_codes ?? [])
      .map((recommendation) => recommendation.icd_code)
      .filter((icdCode) => !deselectedIcdCodes.has(icdCode)),
  );

  function handleToggle(icdCode: ICDCode) {
    setDeselectedIcdCodes((previous) => {
      const next = new Set(previous);
      if (next.has(icdCode)) {
        next.delete(icdCode);
      } else {
        next.add(icdCode);
      }
      return next;
    });
  }

  async function handleSubmit() {
    if (!workflowId) {
      return;
    }

    setSubmitState({ kind: "submitting" });

    try {
      const decision = await submitReviewDecision(workflowId, {
        selected_icd_codes: Array.from(selectedIcdCodes),
      });

      setSubmitState({ kind: "success", decisionId: decision.decision_id });
      setState({
        kind: "loaded",
        review: {
          workflow_id: decision.workflow_id,
          case_id: decision.case_id,
          status: "completed",
          decision_id: decision.decision_id,
          approved_icd_codes: decision.approved_icd_codes,
        },
      });
    } catch (error) {
      const message =
        error instanceof ApiError ? error.detail : "Failed to submit review decision.";
      setSubmitState({ kind: "error", message });
    }
  }

  return (
    <section className="review-page">
      <ReviewHeader
        workflowId={review.workflow_id}
        caseId={review.case_id}
        status={review.status}
      />
      <ReviewStatusBanner status={review.status} />
      <ClinicalContextCard
        reasoningSummary={review.reasoning_summary}
        normalizedNoteText={review.normalized_note_text}
      />
      <RecommendationList
        recommendedIcdCodes={review.recommended_icd_codes}
        approvedIcdCodes={review.approved_icd_codes}
        selection={
          isPendingReview
            ? {
                selectedIcdCodes,
                onToggle: handleToggle,
                disabled: submitState.kind === "submitting",
              }
            : undefined
        }
      />
      {isPendingReview && (
        <div className="decision-submit">
          <button type="button" onClick={handleSubmit} disabled={submitState.kind === "submitting"}>
            {submitState.kind === "submitting" ? "Submitting…" : "Submit decision"}
          </button>
          {submitState.kind === "error" && (
            <p className="review-page__error">{submitState.message}</p>
          )}
        </div>
      )}
    </section>
  );
}