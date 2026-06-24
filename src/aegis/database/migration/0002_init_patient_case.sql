CREATE TABLE IF NOT EXISTS patient_case (
    patient_id TEXT PRIMARY KEY,
    case_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed')),
    ingress_timestamp TEXT NOT NULL,
    raw_clinical_note TEXT NOT NULL,
    anonymized_clinical_note TEXT,
    raw_notes TEXT,
    clinical_notes_clear TEXT,
    icd11_codes TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (patient_id) REFERENCES patient_identity_vault(patient_id)
);
