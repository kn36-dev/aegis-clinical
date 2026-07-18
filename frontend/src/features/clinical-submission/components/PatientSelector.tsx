import { useEffect, useState } from "react";
import { listDemoPatients } from "../../../api/demoApi";
import type { DemoPatientResponse } from "../../../domain/demo";

interface PatientSelectorProps {
  value: string;
  onChange: (patientId: string) => void;
  disabled?: boolean;
  /**
   * Reports whether a non-empty demo patient list resolved, so the parent
   * form can decide whether the raw Patient ID field is the primary input
   * (no demo list) or a manual-entry fallback (demo list present) instead
   * of always showing both at once.
   */
  onAvailabilityChange?: (available: boolean) => void;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "unavailable" }
  | { kind: "available"; patients: DemoPatientResponse[] };

/**
 * Optional convenience over the Patient ID field: fetches
 * GET /api/v1/demo/patients and, only when that returns a non-empty list
 * (i.e. AEGIS_PROFILE == "demo"), offers a dropdown of those fixed,
 * deterministic identities. Renders nothing in every other case — a
 * fetch failure and an empty list (production/integration) are treated
 * identically, since either way the physician still has the free-text
 * Patient ID field to fall back to. This component never invents a
 * patient id itself; it only ever reports one the backend already knows
 * about.
 */
export function PatientSelector({ value, onChange, disabled, onAvailabilityChange }: PatientSelectorProps) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    listDemoPatients()
      .then((patients) => {
        if (cancelled) {
          return;
        }
        const available = patients.length > 0;
        setState(available ? { kind: "available", patients } : { kind: "unavailable" });
        onAvailabilityChange?.(available);
      })
      .catch(() => {
        if (!cancelled) {
          setState({ kind: "unavailable" });
          onAvailabilityChange?.(false);
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
