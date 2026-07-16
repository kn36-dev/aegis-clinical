-- ============================================================================
-- 0011: Clinical Decision - durable, physician-approved clinical truth
-- ============================================================================
--
-- Backs the ClinicalDecisionRepository protocol
-- (aegis.services.persistence_service). Deliberately separate from
-- patient_extracted_code (migration 0004), which is shaped for AI-extraction
-- predictions (confidence_score, extraction_source) that ClinicalDecision's
-- domain contract explicitly excludes.

CREATE TABLE IF NOT EXISTS clinical_decision (

    decision_id TEXT PRIMARY KEY,

    case_id TEXT NOT NULL,

    patient_id_reference TEXT NOT NULL,

    normalization_version TEXT NOT NULL,

    created_at TEXT NOT NULL,

    FOREIGN KEY (case_id)
        REFERENCES patient_case(case_id),

    FOREIGN KEY (patient_id_reference)
        REFERENCES patient_identity_vault(patient_id)

);

CREATE INDEX IF NOT EXISTS idx_clinical_decision_case
ON clinical_decision(case_id);
