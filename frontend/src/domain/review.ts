/**
 * Mirrors aegis.api.schemas.review — the DTOs for
 * GET/POST /api/v1/reviews/{thread_id}...
 */
import type { ICDCode, UUID } from "./common";

export type ReviewWorkflowStatus = "pending_review" | "completed";

export interface RecommendedICDCodeResponse {
  icd_code: ICDCode;
  justification: string;
  model_confidence: number;
  supporting_findings: string[];
  conflicting_findings: string[];
}

export interface ApprovedICDCodeResponse {
  icd_code: ICDCode;
  disposition: string;
}

export interface ReviewStateResponse {
  workflow_id: UUID;
  case_id: UUID;
  status: ReviewWorkflowStatus;

  recommendation_id?: UUID;
  reasoning_summary?: string;
  normalized_note_text?: string;
  recommended_icd_codes?: RecommendedICDCodeResponse[];

  decision_id?: UUID;
  approved_icd_codes?: ApprovedICDCodeResponse[];
}

export interface PhysicianDecisionSubmissionRequest {
  selected_icd_codes: ICDCode[];
}

export interface ReviewDecisionResponse {
  workflow_id: UUID;
  case_id: UUID;
  decision_id: UUID;
  approved_icd_codes: ApprovedICDCodeResponse[];
}
