-- ============================================================================
-- 0009: Clinical Note Content - Sensitive Clinical Narrative
-- ============================================================================

CREATE TABLE IF NOT EXISTS clinical_note_content (

    case_id TEXT PRIMARY KEY,

    encrypted_raw_note BLOB NOT NULL,

    encrypted_anonymized_note BLOB,

    payload_checksum TEXT NOT NULL,

    encryption_version INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL,

    FOREIGN KEY (case_id)
        REFERENCES patient_case(case_id)
        ON DELETE CASCADE

);

CREATE INDEX IF NOT EXISTS idx_clinical_note_content_case
ON clinical_note_content(case_id);