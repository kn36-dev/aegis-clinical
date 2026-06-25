CREATE TABLE IF NOT EXISTS trial_match (
    match_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    trigger_case_id TEXT NOT NULL,
    trial_id TEXT NOT NULL,
    structural_match_score REAL NOT NULL,
    match_status TEXT NOT NULL CHECK (match_status IN ('PENDING_REVIEW', 'PHYSICIAN_APPROVED', 'PHYSICIAN_REJECTED')),
    justification_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,

    UNIQUE(patient_id, trial_id),
    FOREIGN KEY (patient_id) REFERENCES patient_identity_vault(patient_id),
    FOREIGN KEY (trigger_case_id) REFERENCES patient_case(case_id) ON DELETE CASCADE,
    FOREIGN KEY (trial_id) REFERENCES clinical_trial(trial_id) ON DELETE CASCADE
);

-- trigger_case_id (the exact latest case that makes the patient eligible)
-- trial_id (the exact trial that fulfills all eligibilities)
-- structural_match_score (0.0 to 1.0) 
-- (Can be enhanced with NLP, fuzzy matching so it's not binary)
-- justification_summary (filled by matching engine OR physician)