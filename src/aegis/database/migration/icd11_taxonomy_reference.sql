CREATE TABLE IF NOT EXISTS icd11_taxonomy (
            code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            class_kind TEXT NOT NULL,
            context_path TEXT NOT NULL
        );