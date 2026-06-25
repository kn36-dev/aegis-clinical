CREATE TABLE IF NOT EXISTS patient_case (
    case_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,


    -- Canonical mapping to the LangGraph workflow instance.
    -- Allows deterministic HITL resume operations and checkpoint
    -- lookups without inspecting serialized checkpoint state.
    thread_id TEXT NOT NULL UNIQUE,
    

    status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed', 'completed')),
    ingress_timestamp TEXT NOT NULL,

    raw_clinical_note TEXT NOT NULL,
    anonymized_clinical_note TEXT,

    version INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (patient_id) REFERENCES patient_identity_vault(patient_id)
);
