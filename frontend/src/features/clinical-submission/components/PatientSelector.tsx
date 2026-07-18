import { useEffect, useState } from "react";
import { listDemoPatients } from "../../../api/demoApi";
import type { DemoPatientResponse } from "../../../domain/demo";

interface PatientSelectorProps {
  value: string;
  onChange: (patientId: string) => void;
  disabled?: boolean;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "unavailable" }
  | { kind: "available"; patients: DemoPatientResponse[] };

/**
 * Optional convenience over the Patient ID field below it: fetches
 * GET /api/v1/demo/patients and, only when that returns a non-empty list
 * (i.e. AEGIS_PROFILE == "demo"), offers a dropdown of those fixed,
 * deterministic identities. Renders nothing in every other case — a
 * fetch failure and an empty list (production/integration) are treated
 * identically, since either way the physician still has the free-text
 * Patient ID field to fall back to. This component never invents a
 * patient id itself; it only ever reports one the backend already knows
 * about.
 */
export function PatientSelector({ value, onChange, disabled }: PatientSelectorProps) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    listDemoPatients()
      .then((patients) => {
        if (cancelled) {
          return;
        }
        setState(patients.length > 0 ? { kind: "available", patients } : { kind: "unavailable" });
      })
      .catch(() => {
        if (!cancelled) {
          setState({ kind: "unavailable" });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind !== "available") {
    return null;
  }

  return (
    <label className="clinical-submission-form__field">
      <span>Demo patient</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
      >
        <option value="">Select a demo patient…</option>
        {state.patients.map((patient) => (
          <option key={patient.patient_id} value={patient.patient_id}>
            {patient.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
