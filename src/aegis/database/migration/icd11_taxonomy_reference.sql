CREATE TABLE IF NOT EXISTS ICD11_taxonomy_reference (
            icd11_code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            hierarchical_path TEXT NOT NULL,
            description TEXT
        );