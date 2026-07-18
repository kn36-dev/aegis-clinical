/**
 * Mirrors aegis.api.schemas.clinical — the DTOs for
 * POST /api/v1/clinical-notes.
 */
import type { ICDCode, UUID } from "./common";

export type WorkflowStatus = "pending_review" | "completed";

export interface ClinicalNoteIngestionRequest {
  patient_id: UUID;
  content_reference: string;
}

export interface ApprovedICDCodeResponse {
  icd_code: ICDCode;
  disposition: string;
}

export interface ClinicalNoteIngestionResponse {
  workflow_id: UUID;
  case_id: UUID;
  status: WorkflowStatus;
  decision_id?: UUID;
  approved_icd_codes?: ApprovedICDCodeResponse[];
}
