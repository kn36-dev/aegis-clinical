-- ============================================================================
-- 0012: Approved ICD Classification - physician disposition per approved code
-- ============================================================================
--
-- One row per ApprovedICDClassification on a ClinicalDecision. disposition
-- (accepted/added/removed/modified) records the physician's relationship to
-- the AI recommendation, per RecommendationDisposition
-- (aegis.models.clinical_decision). sequence_index preserves the original
-- ordering of ClinicalDecision.approved_icd_codes for round-trip fidelity;
-- it is a persistence-mapping detail, not clinical meaning.

CREATE TABLE IF NOT EXISTS approved_icd_classification (

    decision_id TEXT NOT NULL,

    icd_code TEXT NOT NULL,

    disposition TEXT NOT NULL CHECK (
        disposition IN ('accepted', 'added', 'removed', 'modified')
    ),

    sequence_index INTEGER NOT NULL,

    PRIMARY KEY (decision_id, icd_code),

    FOREIGN KEY (decision_id)
        REFERENCES clinical_decision(decision_id)
        ON DELETE CASCADE,

    FOREIGN KEY (icd_code)
        REFERENCES icd11_taxonomy(code)

);
