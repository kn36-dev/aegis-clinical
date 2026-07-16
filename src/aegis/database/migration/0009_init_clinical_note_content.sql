-- ============================================================================
-- 0009: Clinical Note Content - Content Storage Provider boundary
-- ============================================================================
--
-- Backs the ClinicalNoteContentRepository protocol
-- (aegis.services.normalization_service). content_reference is the opaque
-- pointer already carried on ClinicalNote; it is the primary key here so a
-- reference can be resolved without depending on case_id cardinality.
--
-- This table currently stores plaintext content_payload. It is intentionally
-- a Content Storage Provider boundary, not an encryption boundary: no
-- encryption is assumed or implemented here. A future encrypted-at-rest
-- implementation (e.g. an EncryptedClinicalContentStore) can replace the
-- SQLite adapter behind ClinicalNoteContentRepository without changing this
-- table's role in the schema.

CREATE TABLE IF NOT EXISTS clinical_note_content (

    content_reference TEXT PRIMARY KEY,

    case_id TEXT NOT NULL,

    content_payload TEXT NOT NULL,

    checksum TEXT NOT NULL,

    created_at TEXT NOT NULL,

    FOREIGN KEY (case_id)
        REFERENCES patient_case(case_id)
        ON DELETE CASCADE

);

CREATE INDEX IF NOT EXISTS idx_clinical_note_content_case
ON clinical_note_content(case_id);
