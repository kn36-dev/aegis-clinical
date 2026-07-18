import type { ICDCode } from "../../../domain/common";
import type { ApprovedICDCodeResponse, RecommendedICDCodeResponse } from "../../../domain/review";

export interface RecommendationSelection {
  selectedIcdCodes: ReadonlySet<ICDCode>;
  onToggle: (icdCode: ICDCode) => void;
  disabled?: boolean;
}

interface RecommendationListProps {
  recommendedIcdCodes?: RecommendedICDCodeResponse[];
  approvedIcdCodes?: ApprovedICDCodeResponse[];
  /**
   * When supplied, the pending-review branch renders a checkbox per
   * recommendation so a physician can choose which codes to approve.
   * Selection state and the submit lifecycle live in DecisionDetailPage —
   * this component only renders the given selection and reports toggles.
   */
  selection?: RecommendationSelection;
}

/**
 * Displays ICD-11 codes for a workflow. Shows AI recommendations (pending
 * review) or the already-approved codes (completed review) — never both,
 * since the API only ever populates one side per `ReviewStateResponse`.
 */
export function RecommendationList({
  recommendedIcdCodes,
  approvedIcdCodes,
  selection,
}: RecommendationListProps) {
  if (approvedIcdCodes) {
    return (
      <section className="recommendation-list">
        <h2>Approved ICD-11 Codes</h2>
        <ul className="recommendation-list__items">
          {approvedIcdCodes.map((code) => (
            <li key={code.icd_code} className="recommendation-card">
              <div className="recommendation-card__header">
                <code>{code.icd_code}</code>
                <span className="recommendation-card__disposition">{code.disposition}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  if (!recommendedIcdCodes || recommendedIcdCodes.length === 0) {
    return (
      <section className="recommendation-list">
        <h2>Recommended ICD-11 Codes</h2>
        <p>No AI recommendations are attached to this workflow.</p>
      </section>
    );
  }

  return (
    <section className="recommendation-list">
      <h2>Recommended ICD-11 Codes</h2>
      <ul className="recommendation-list__items">
        {recommendedIcdCodes.map((recommendation) => (
          <li key={recommendation.icd_code} className="recommendation-card">
            <div className="recommendation-card__header">
              {selection ? (
                <label className="recommendation-card__select">
                  <input
                    type="checkbox"
                    checked={selection.selectedIcdCodes.has(recommendation.icd_code)}
                    disabled={selection.disabled}
                    onChange={() => selection.onToggle(recommendation.icd_code)}
                  />
                  <code>{recommendation.icd_code}</code>
                </label>
              ) : (
                <code>{recommendation.icd_code}</code>
              )}
              <span className="recommendation-card__confidence">
                {Math.round(recommendation.model_confidence * 100)}% model confidence
              </span>
            </div>
            <p className="recommendation-card__justification">{recommendation.justification}</p>
            {recommendation.supporting_findings.length > 0 && (
              <div className="recommendation-card__findings">
                <h4>Supporting findings</h4>
                <ul>
                  {recommendation.supporting_findings.map((finding) => (
                    <li key={finding}>{finding}</li>
                  ))}
                </ul>
              </div>
            )}
            {recommendation.conflicting_findings.length > 0 && (
              <div className="recommendation-card__findings recommendation-card__findings--conflicting">
                <h4>Conflicting findings</h4>
                <ul>
                  {recommendation.conflicting_findings.map((finding) => (
                    <li key={finding}>{finding}</li>
                  ))}
                </ul>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
