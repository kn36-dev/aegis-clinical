import { httpClient } from "./httpClient";
import type { DemoPatientResponse } from "../domain/demo";

/** GET /api/v1/demo/patients — see aegis.api.routers.demo.list_demo_patients. */
export function listDemoPatients(): Promise<DemoPatientResponse[]> {
  return httpClient.get<DemoPatientResponse[]>("/api/v1/demo/patients");
}
