import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { ingestClinicalNote } from "../../api/clinicalApi";
import { ApiError } from "../../api/httpClient";
import type { ClinicalNoteIngestionResponse } from "../../domain/clinical";
import { WorkflowStageTimeline } from "../workflow-visibility/WorkflowStageTimeline";
import { PatientSelector } from "./components/PatientSelector";

type SubmitState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; result: ClinicalNoteIngestionResponse }
  | { kind: "error"; message: string };

const STATUS_MESSAGE: Record<ClinicalNoteIngestionResponse["status"], string> = {
  pending_review: "Submitted. This case is pending physician review.",
  completed: "Submitted. The workflow completed automatically (e.g. a cache hit) with no review pending.",
};

/**
 * POST /api/v1/clinical-notes/ingest — see aegis.api.routers.clinical.ingest_clinical_note.
 *
 * The sibling endpoint, POST /api/v1/clinical-notes, requires a caller to
 * already hold a `content_reference` pointing at previously-stored note
 * content — there is no UI-reachable way to mint one, and
 * docs/tradeoffs_and_limitations.md documents that a fresh submission
 * through it 502s against the real, credential-backed runtime (the
 * "Live-Credential Content Seeding Gap"). `/ingest` is the endpoint built
 * to close that gap for exactly this case: a caller with raw note text and
 * no pre-existing reference, which is what a physician typing a note into
 * this page has.
 */
export function ClinicalSubmissionPage() {
  const [patientId, setPatientId] = useState("");
  const [noteText, setNoteText] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });
  const [demoPatientsAvailable, setDemoPatientsAvailable] = useState(false);
  const [manualEntryOpen, setManualEntryOpen] = useState(false);

  const isSubmitting = submitState.kind === "submitting";
  const showManualField = !demoPatientsAvailable || manualEntryOpen;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!patientId.trim()) {
      setSubmitState({ kind: "error", message: "Select or enter a patient id." });
      return;
    }

    setSubmitState({ kind: "submitting" });

    try {
      const result = await ingestClinicalNote({
        patient_id: patientId.trim(),
        note_text: noteText,
      });
      setSubmitState({ kind: "success", result });
    } catch (error) {
      const message =
        error instanceof ApiError ? error.detail : "Failed to submit clinical note.";
      setSubmitState({ kind: "error", message });
    }
  }

  return (
    <section className="clinical-submission-page">
      <h1>Clinical Submission</h1>
      <p>
        Submit a clinical note for AI-assisted ICD-11 coding. A deterministic pipeline
        retrieves evidence and a bounded AI reasoning step proposes recommendations; a
        physician reviews before anything is written to the clinical record.
      </p>

      <form className="clinical-submission-form" onSubmit={handleSubmit}>
        <PatientSelector
          value={patientId}
          onChange={setPatientId}
          disabled={isSubmitting}
          onAvailabilityChange={setDemoPatientsAvailable}
        />
        {showManualField ? (
          <label className="clinical-submission-form__field">
            <span>Patient ID</span>
            <input
              type="text"
              value={patientId}
              onChange={(event) => setPatientId(event.target.value)}
              placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
              disabled={isSubmitting}
            />
          </label>
        ) : (
          <button
            type="button"
            className="clinical-submission-form__manual-toggle"
            onClick={() => setManualEntryOpen(true)}
            disabled={isSubmitting}
          >
            Enter Patient ID manually instead
          </button>
        )}
        <label className="clinical-submission-form__field">
          <span>Clinical note text</span>
          <textarea
            value={noteText}
            onChange={(event) => setNoteText(event.target.value)}
            rows={12}
            required
            disabled={isSubmitting}
          />
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting…" : "Submit clinical note"}
        </button>
      </form>

      {submitState.kind === "error" && (
        <p className="clinical-submission-page__error" role="alert">
          {submitState.message}
        </p>
      )}

      {submitState.kind === "success" && <SubmissionResult result={submitState.result} />}
    </section>
  );
}

function SubmissionResult({ result }: { result: ClinicalNoteIngestionResponse }) {
  return (
    <div className="clinical-submission-result" role="status" aria-live="polite">
      <p>{STATUS_MESSAGE[result.status]}</p>
      <WorkflowStageTimeline status={result.status} />
      <dl className="clinical-submission-result__meta">
        <div>
          <dt>Case ID</dt>
          <dd>
            <code>{result.case_id}</code>
          </dd>
        </div>
        <div>
          <dt>Workflow ID</dt>
          <dd>
            <code>{result.workflow_id}</code>
          </dd>
        </div>
      </dl>
      <Link to={`/reviews/${result.workflow_id}`}>View workflow</Link>
    </div>
  );
}
