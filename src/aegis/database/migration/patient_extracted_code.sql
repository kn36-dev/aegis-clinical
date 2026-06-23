CREATE TABLE IF NOT EXISTS Patient_extracted_codes (
            case_id TEXT NOT NULL,
            icd11_code TEXT NOT NULL,
            confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
            extraction_source TEXT NOT NULL,
            PRIMARY KEY (case_id, icd11_code),
            FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
            FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
        );