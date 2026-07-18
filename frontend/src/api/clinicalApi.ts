import { httpClient } from "./httpClient";
import type {
  ClinicalNoteIngestionRequest,
  ClinicalNoteIngestionResponse,
  ClinicalNoteIngestionWithContentRequest,
} from "../domain/clinical";

/** POST /api/v1/clinical-notes — see aegis.api.routers.clinical.submit_clinical_note. */
export function submitClinicalNote(
  payload: ClinicalNoteIngestionRequest,
): Promise<ClinicalNoteIngestionResponse> {
  return httpClient.post<ClinicalNoteIngestionResponse>("/api/v1/clinical-notes", payload);
}

/** POST /api/v1/clinical-notes/ingest — see aegis.api.routers.clinical.ingest_clinical_note. */
export function ingestClinicalNote(
  payload: ClinicalNoteIngestionWithContentRequest,
): Promise<ClinicalNoteIngestionResponse> {
  return httpClient.post<ClinicalNoteIngestionResponse>("/api/v1/clinical-notes/ingest", payload);
}
