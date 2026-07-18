/**
 * Mirrors aegis.api.schemas.demo — the DTO for GET /api/v1/demo/patients.
 */
import type { UUID } from "./common";

export interface DemoPatientResponse {
  patient_id: UUID;
  display_name: string;
}
