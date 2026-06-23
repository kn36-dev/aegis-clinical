CREATE TABLE IF NOT EXISTS Trial_Matches (
            match_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            trigger_case_id TEXT NOT NULL,
            trial_id TEXT NOT NULL,
            structural_match_score REAL NOT NULL,
            match_status TEXT NOT NULL CHECK (match_status IN ('PENDING_REVIEW', 'PHYSICIAN_APPROVED', 'PHYSICIAN_REJECTED')),
            justification_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id),
            FOREIGN KEY (trigger_case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
            FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE
        );