CREATE TABLE IF NOT EXISTS Trial_Target_codes (
            trial_id TEXT NOT NULL,
            icd11_code TEXT NOT NULL,
            criterion_type TEXT NOT NULL CHECK (criterion_type IN ('INCLUSION', 'EXCLUSION')),
            PRIMARY KEY (trial_id, icd11_code),
            FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE,
            FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
        );