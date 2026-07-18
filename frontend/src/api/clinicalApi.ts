import { httpClient } from "./httpClient";
import type { ClinicalNoteIngestionRequest, ClinicalNoteIngestionResponse } from "../domain/clinical";

/** POST /api/v1/clinical-notes — see aegis.api.routers.clinical.submit_clinical_note. */
export function submitClinicalNote(
  payload: ClinicalNoteIngestionRequest,
): Promise<ClinicalNoteIngestionResponse> {
  return httpClient.post<ClinicalNoteIngestionResponse>("/api/v1/clinical-notes", payload);
}
