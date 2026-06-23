CREATE TABLE IF NOT EXISTS Patient_identity_vault (
            patient_id TEXT PRIMARY KEY,
            medical_record_number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth DATE NOT NULL
        );