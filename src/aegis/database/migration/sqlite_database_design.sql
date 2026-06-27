-- ============================================================================
-- AEGIS Clinical Database Full Schema
-- ============================================================================
-- This file contains the complete database schema combining all migrations
-- in sequence: from initialization through human review logging.
-- The conn.execute("PRAGMA foreign_keys = ON") is configured before this.
-- ============================================================================


-- ============================================================================
-- 0001: Checkpoint Blob Table - Workflow State Management
-- ============================================================================

CREATE TABLE IF NOT EXISTS checkpoint_blob (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_id TEXT,             -- The previous step's checkpoint_id
    checkpoint BLOB NOT NULL,   -- The state (what has happened)
    metadata BLOB NOT NULL,     -- The how (llm model, token consume)
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- We can use CheckpointNotLatest error
-- To provide 409 by using thread_id and checkpoint_id
-- Example code in src/aegis/graphs/optimistic_locking.py

-- Instead of a full BLOB, refer to what's available in OTel
-- Read more about the metadata and OTel in limitations and tradeoffs.md

-- ### Separation of Checkpoint State and Telemetry Data
-- Checkpoint metadata intentionally stores only trace correlation identifiers (for example, `trace_id`) rather than full OpenTelemetry span payloads. This keeps checkpoint storage compact and optimized for workflow resumption, Human-in-the-Loop (HITL) interactions, and state recovery.
-- Detailed execution telemetry, including span timing, token usage metrics, and runtime diagnostics, is emitted separately through OpenTelemetry exporters and written to local development logs. This allows workflow state and observability data to evolve independently while keeping the checkpoint database lightweight and easy to inspect.
-- For production-scale deployments, telemetry would typically be exported via OTLP to a dedicated observability platform such as Jaeger, Grafana Tempo, OpenObserve, or another OpenTelemetry-compatible backend. The portfolio implementation intentionally keeps observability infrastructure minimal to prioritize reproducibility and ease of setup while still demonstrating trace correlation and instrumentation patterns.


-- ============================================================================
-- 0001: Patient Identity Vault - De-identification & HIPAA Compliance
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_identity_vault (
    patient_id TEXT PRIMARY KEY,
    medical_record_number TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL
);


-- ============================================================================
-- 0002: Patient Case - Clinical Note Ingestion & Case Management
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_case (
    case_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,


    -- Canonical mapping to the LangGraph workflow instance.
    -- Allows deterministic HITL resume operations and checkpoint
    -- lookups without inspecting serialized checkpoint state.
    thread_id TEXT NOT NULL UNIQUE,
    

    status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed', 'completed')),
    ingress_timestamp TEXT NOT NULL, -- ISO8601 UTC

    raw_clinical_note TEXT NOT NULL,
    anonymized_clinical_note TEXT,

    version INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (patient_id) REFERENCES patient_identity_vault(patient_id)
);


-- ============================================================================
-- 0003: ICD-11 Taxonomy Reference - Medical Code Standardization
-- ============================================================================

CREATE TABLE IF NOT EXISTS icd11_taxonomy_reference (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    class_kind TEXT NOT NULL,
    context_path TEXT NOT NULL
);

-- Example value
-- Code:         1A03.Z
-- Title:        Intestinal infections due to Escherichia coli, unspecified
-- Class Kind:   category
-- Context Path: Gastroenteritis or colitis of infectious origin > Bacterial intestinal infections > Intestinal infections due to Escherichia coli > Intestinal infections due to Escherichia coli, unspecified


-- ============================================================================
-- 0004: Patient Extracted Code - AI-Generated Medical Codes
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_extracted_code (
    case_id TEXT NOT NULL,
    icd11_code TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    -- Source could be crewAI, LLM, or Physician
    -- Could be improved by an enum
    extraction_source TEXT NOT NULL,
    PRIMARY KEY (case_id, icd11_code),
    FOREIGN KEY (case_id) REFERENCES patient_case(case_id) ON DELETE CASCADE,
    FOREIGN KEY (icd11_code) REFERENCES icd11_taxonomy_reference(code)
);

-- Remember, here 1 icd11_code translates to 1 row
-- So 1 case_id can have multiple rows (1 medical case could diagnose multiple diseases)


-- ============================================================================
-- 0005: Clinical Trial - Recruitment Cohort Eligibility
-- ============================================================================

CREATE TABLE IF NOT EXISTS clinical_trial (
    trial_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4')),
    sponsor TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Recruiting', 'Completed', 'Suspended')),
    raw_eligibility_criteria TEXT NOT NULL
);

-- A trial is always unique, so primary key
-- Title: human-readable semantic label
-- Sponsor: Compliance Segmentation, Institutional Reporting, Downstream Analytics 
-- (which pharma sponsors dominate which ICD clusters)
-- raw_eligibility_criteria: LLM semantic parser, embedding, rule extraction
-- Phase: commonly represent things like:
-- Phase 1 → healthy volunteers, high safety margin
-- Phase 2 → small patient groups, early efficacy
-- Phase 3 → large population, stricter inclusion criteria
-- Phase 4 → post-market real-world patients

-- Normally the embedding is title + eligibility_criteria + phase metadata


-- ============================================================================
-- 0006: Trial Target Code - Trial Inclusion/Exclusion Criteria
-- ============================================================================

CREATE TABLE IF NOT EXISTS trial_target_code (
    trial_id TEXT NOT NULL,
    icd11_code TEXT NOT NULL,
    criterion_type TEXT NOT NULL CHECK (criterion_type IN ('INCLUSION', 'EXCLUSION')),
    PRIMARY KEY (trial_id, icd11_code),
    FOREIGN KEY (trial_id) REFERENCES clinical_trial(trial_id) ON DELETE CASCADE,
    FOREIGN KEY (icd11_code) REFERENCES icd11_taxonomy_reference(code)
);

-- EXPLANATION:

-- For each patient:

-- Required Trial Codes
--     minus
-- Patient Codes

-- must be empty

-- AND

-- Excluded Trial Codes
--     intersect
-- Patient Codes

-- must be empty.

-- WITH patient_icd_profile AS (
--     SELECT DISTINCT
--         pc.patient_id,
--         pec.icd11_code
--     FROM patient_case pc
--     JOIN patient_extracted_code pec
--         ON pc.case_id = pec.case_id
-- )

-- SELECT DISTINCT p.patient_id
-- FROM patient_icd_profile p
-- WHERE

--     NOT EXISTS (
--         SELECT t.icd11_code
--         FROM trial_target_code t
--         WHERE t.trial_id = 'NCT001'
--           AND t.criterion_type = 'INCLUSION'

--         EXCEPT

--         SELECT p2.icd11_code
--         FROM patient_icd_profile p2
--         WHERE p2.patient_id = p.patient_id
--     )

--     AND

--     NOT EXISTS (
--         SELECT t.icd11_code
--         FROM trial_target_code t
--         WHERE t.trial_id = 'NCT001'
--           AND t.criterion_type = 'EXCLUSION'

--         INTERSECT

--         SELECT p2.icd11_code
--         FROM patient_icd_profile p2
--         WHERE p2.patient_id = p.patient_id
--     );


-- ============================================================================
-- 0007: Trial Match - Matching Decisions & Review Status
-- ============================================================================

CREATE TABLE IF NOT EXISTS trial_match (
    match_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    trigger_case_id TEXT NOT NULL,
    trial_id TEXT NOT NULL,
    structural_match_score REAL NOT NULL
    CHECK (
        structural_match_score >= 0.0
        AND structural_match_score <= 1.0
    ),
    match_status TEXT NOT NULL CHECK (match_status IN ('PENDING_REVIEW', 'PHYSICIAN_APPROVED', 'PHYSICIAN_REJECTED')),
    justification_summary TEXT NOT NULL,
    created_at TEXT NOT NULL, -- ISO8601 UTC

    UNIQUE(patient_id, trial_id),
    FOREIGN KEY (patient_id) REFERENCES patient_identity_vault(patient_id),
    FOREIGN KEY (trigger_case_id) REFERENCES patient_case(case_id) ON DELETE CASCADE,
    FOREIGN KEY (trial_id) REFERENCES clinical_trial(trial_id) ON DELETE CASCADE
);

-- trigger_case_id (the exact latest case that makes the patient eligible)
-- trial_id (the exact trial that fulfills all eligibilities)
-- structural_match_score (0.0 to 1.0) 
-- (Can be enhanced with NLP, fuzzy matching so it's not binary)
-- justification_summary (filled by matching engine OR physician)


-- ============================================================================
-- 0008: Human Review Logs - Audit Trail & Physician Actions
-- ============================================================================

CREATE TABLE IF NOT EXISTS human_review_log (
    review_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    reviewer_badge_id TEXT NOT NULL,
    action_taken TEXT NOT NULL CHECK (action_taken IN ('APPROVED_ALL', 'OVERRIDDEN_AND_APPROVED', 'REJECTED_CASE')),
    physician_notes TEXT,
    cryptographic_signature TEXT NOT NULL,
    timestamp TEXT NOT NULL, -- ISO8601 UTC
    FOREIGN KEY (case_id) REFERENCES patient_case(case_id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_patient_case_patient_id
ON patient_case(patient_id);

CREATE INDEX IF NOT EXISTS idx_patient_extracted_code_case
ON patient_extracted_code(case_id);

CREATE INDEX IF NOT EXISTS idx_patient_extracted_code_icd
ON patient_extracted_code(icd11_code);

CREATE INDEX IF NOT EXISTS idx_trial_target_code_icd
ON trial_target_code(icd11_code);

CREATE INDEX IF NOT EXISTS idx_trial_match_patient
ON trial_match(patient_id);

CREATE INDEX IF NOT EXISTS idx_trial_match_trial
ON trial_match(trial_id);

CREATE INDEX IF NOT EXISTS idx_human_review_log_case
ON human_review_log(case_id);

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
