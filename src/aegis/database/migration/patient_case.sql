CREATE TABLE IF NOT EXISTS Patient_cases (
            case_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed')),
            ingress_timestamp TEXT NOT NULL,
            raw_clinical_note TEXT NOT NULL,
            anonymized_clinical_note TEXT,
            FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id)
        );