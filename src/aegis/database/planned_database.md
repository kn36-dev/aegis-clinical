# SYSTEM ARCHITECTURE COMPONENT: COMPLETE PARADIGM DATABASE SCHEMA DEFINITION
# Project: aegis-clinical 🛡️
# Architect: Principal AI System Architect
# Classification: Medical-Grade Enterprise Data Engine (HIPAA-Compliant Isolation)

This document establishes the definitive, immutable multi-paradigm storage layer layout for the Aegis clinical engine. It explicitly captures every column, constraint, data boundary, and cross-paradigm identifier link to guarantee complete architectural protection against data loss, concurrent race conditions, or catastrophic temporal amnesia (the clinical data fragmentation blind spot).

---

## 🏗️ MACRO PARADIGM ARCHITECTURE & RELATIONSHIP MAP

```text
+-----------------------------------------------------------------------------------+
|                              AEGIS DATA INFRASTRUCTURE                            |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [SQLITE RELATIONAL DATA ENGINE]             [UPSTASH VECTOR SEMANTIC INDEX]      |
|  +--------------------------------+          +----------------------------------+ |
|  | Patient_identity_vault         |          | Index: icd11_taxonomy_embeddings | |
|  |  └── patient_id  ──────────────┼──────────┼──> Metadata: icd11_code          | |
|  |                                |          |                                  | |
|  | Patient_cases                  |          | Index: patient_narratives        | |
|  |  ├── case_id                   |          |  └── Metadata: patient_id        | |
|  |  └── patient_id                |          |                                  | |
|  |                                |          | Index: trial_protocols           | |
|  | ICD11_taxonomy_reference       |          |  └── Metadata: trial_id          | |
|  |  └── icd11_code                |          |                                  | |
|  |                                |          | Index: semantic_llm_cache        | |
|  | Patient_extracted_codes        |          +----------------------------------+ |
|  |                                |                                               |
|  | Clinical_trial                 |          [UPSTASH REDIS COORDINATION LAYER]   |
|  |  └── trial_id                  |          +----------------------------------+ |
|  |                                |          | Key: rate_limit:groq_api_gate    | |
|  | Trial_Target_codes             |          | Key: lock:case_id:{id}           | |
|  |                                |          +----------------------------------+ |
|  | Trial_Matches                  |                                               |
|  |  ├── patient_id (Cumulative)   |          [LANGGRAPH PERSISTENT CHANNELS]      |
|  |  └── trigger_case_id           |          +----------------------------------+ |
|  |                                |          | Table: checkpoint_blob          | |
|  | Human_Review_Logs              |          +----------------------------------+ |
|  +--------------------------------+                                               |
+-----------------------------------------------------------------------------------+
```

---

## 💾 1. STRUCTURED LAYER: RELATIONAL ENGINE (SQLite Specification)

### A. ZERO-KNOWLEDGE PATIENT IDENTIFICATION VAULT
*Purpose: Complete logical isolation of Protected Health Information (PHI). Processing servers only handle the non-PII `patient_id` UUID.*

```sql
CREATE TABLE Patient_identity_vault (
    patient_id TEXT PRIMARY KEY,               -- Cryptographically unique UUIDv4
    medical_record_number TEXT UNIQUE NOT NULL,-- Masked real-world hospital identification string
    first_name TEXT NOT NULL,                  -- Real patient given name (Encrypted at rest in deployment)
    last_name TEXT NOT NULL,                   -- Real patient surname (Encrypted at rest in deployment)
    date_of_birth DATE NOT NULL                -- ISO YYYY-MM-DD format for demographic constraint checks
);
```

### B. SYSTEM INFERENCE CORE & DIAGNOSTIC TRACKING
*Purpose: Tracks separate clinical encounter lifecycles while maintaining strict foreign key relationships back to the patient identity layer.*

```sql
CREATE TABLE Patient_cases (
    case_id TEXT PRIMARY KEY,                  -- Unique UUIDv4 transaction identifier
    patient_id TEXT NOT NULL,                  -- Foreign Key pointing to Patient_identity_vault(patient_id)
    status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed')),
    ingress_timestamp TEXT NOT NULL,           -- ISO-8601 UTC timestamp string (e.g., "2026-06-20T14:27:00Z")
    raw_clinical_note TEXT NOT NULL,           -- Unstructured, raw doctor-entered text record
    anonymized_clinical_note TEXT,             -- Scrubbed text containing 0% PHI elements, safe for LLM ingestion
    FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id)
);

CREATE TABLE ICD11_taxonomy_reference (
    icd11_code TEXT PRIMARY KEY,               -- Standardized ICD-11 Alpha-Numeric Code identifier (e.g., "1A40")
    title TEXT NOT NULL,                       -- Official clinical classification label name
    hierarchical_path TEXT NOT NULL,           -- Complete taxonomic lineage tree used for LLM context injection
    description TEXT                           -- Diagnostic boundary definition details
);

CREATE TABLE Patient_extracted_codes (
    case_id TEXT NOT NULL,                     -- Foreign Key pointing to Patient_cases(case_id)
    icd11_code TEXT NOT NULL,                  -- Foreign Key pointing to ICD11_taxonomy_reference(icd11_code)
    confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0), -- Extraction model certainty index
    extraction_source TEXT NOT NULL,           -- Runtime origin: 'crewai_parsing_agent' OR 'physician_override'
    PRIMARY KEY (case_id, icd11_code),         -- Prevents duplicate entry of a code inside a single ingestion instance
    FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
);
```

### C. CLINICAL TRIAL MATRIX & TARGET EXTRACTION
*Purpose: Maps research profiles, legal criteria schemas, and baseline inclusion/exclusion indicators.*

```sql
CREATE TABLE Clinical_trial (
    trial_id TEXT PRIMARY KEY,                 -- Pinned ClinicalTrials.gov Registry ID identifier (e.g., "NCT05912345")
    title TEXT NOT NULL,                       -- Official research trial study name
    phase TEXT NOT NULL CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4')),
    sponsor TEXT NOT NULL,                     -- Organizing hospital system or biopharma entity
    status TEXT NOT NULL CHECK (status IN ('Recruiting', 'Completed', 'Suspended')),
    raw_eligibility_criteria TEXT NOT NULL     -- Complete long-form unstructured text of research requirements
);

CREATE TABLE Trial_Target_codes (
    trial_id TEXT NOT NULL,                    -- Foreign Key pointing to Clinical_trial(trial_id)
    icd11_code TEXT NOT NULL,                  -- Foreign Key pointing to ICD11_taxonomy_reference(icd11_code)
    criterion_type TEXT NOT NULL CHECK (criterion_type IN ('INCLUSION', 'EXCLUSION')), -- Directional filtering guard
    PRIMARY KEY (trial_id, icd11_code),
    FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE,
    FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
);
```

### D. CRITICAL LONGITUDINAL INTEGRITY MAPS & AUDIT LOGS
*Purpose: Mitigates the "Adam Blindspot" (Temporal Data Fragmentation) by evaluation at the patient entity level, while tracking the historical system trigger context.*

```sql
CREATE TABLE Trial_Matches (
    match_id TEXT PRIMARY KEY,                 -- Unique UUIDv4 matching record token
    patient_id TEXT NOT NULL,                  -- FIXED: The cumulative patient entity evaluated across ALL histories
    trigger_case_id TEXT NOT NULL,             -- The specific, localized ingestion encounter that caused this inference
    trial_id TEXT NOT NULL,                    -- Foreign Key pointing to Clinical_trial(trial_id)
    structural_match_score REAL NOT NULL,      -- Pure, math-derived matching score from target-to-patient profile crossover
    match_status TEXT NOT NULL CHECK (match_status IN ('PENDING_REVIEW', 'PHYSICIAN_APPROVED', 'PHYSICIAN_REJECTED')),
    justification_summary TEXT NOT NULL,       -- Structured, deterministic LLM-generated rationale citing whole profile history
    created_at TEXT NOT NULL,                  -- ISO-8601 creation generation timestamp
    FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id),
    FOREIGN KEY (trigger_case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE
);

CREATE TABLE Human_Review_Logs (
    review_id TEXT PRIMARY KEY,                -- Unique UUIDv4 review record identifier
    case_id TEXT NOT NULL,                     -- Foreign Key pointing to Patient_cases(case_id)
    reviewer_badge_id TEXT NOT NULL,           -- Encrypted hash identifying the signing physician MD
    action_taken TEXT NOT NULL CHECK (action_taken IN ('APPROVED_ALL', 'OVERRIDDEN_AND_APPROVED', 'REJECTED_CASE')),
    physician_notes TEXT,                      -- Detailed context explaining additions/deletions of codes
    cryptographic_signature TEXT NOT NULL,     -- HMAC hash of match state ensuring un-tampered data validation history
    timestamp TEXT NOT NULL,                   -- ISO-8601 sign-off checkpoint timestamp
    FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id)
);
```

### E. STATE ENGINE RUNTIME CORRIDOR (Internal LangGraph Persistent Fabric)
```sql
CREATE TABLE checkpoint_blob (
    thread_id TEXT NOT NULL,                   -- LangGraph operational thread tracking token (corresponds to case_id)
    checkpoint_id TEXT NOT NULL,               -- Unique state ID generation tracking string
    parent_id TEXT,                            -- Ancestral parent checkpoint token for deep branching evaluation
    checkpoint BLOB NOT NULL,                  -- Raw binary serialization of current thread memory/variable state
    metadata BLOB NOT NULL,                    -- Meta configurations capturing routing paths and execution states
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

---

## 🔍 2. UNSTRUCTURED SEMANTIC LAYER: VECTOR EMBEDDING SPACES (Upstash Vector)

*Configuration Variable: Global Space Dimensionality = 1536 (`text-embedding-3-small`). Metrics Platform Matrix: Cosine Distance ($cos(\theta)$).*

### Index A: `patient_narratives`
* **Purpose:** Allows structural parsing agents to locate historically similar colloquial symptom descriptions.
* **Document Vector String Template:** `[Scrubbed text block detailing historical symptoms and presentation history]`
* **Metadata Fields (Strict JSON Property Schema):**
  ```json
  {
    "patient_id": "string (UUIDv4 Reference matching SQLite Exactly)",
    "case_id": "string (UUIDv4 Reference matching SQLite Exactly)",
    "anonymized_status": "string ('CLEAN')"
  }
  ```

### Index B: `trial_protocols`
* **Purpose:** Enables CrewAI matching agents to quickly query semantic subsections of large-scale research papers.
* **Document Vector String Template:** `Section: [Title] Sub-Protocol Requirement Block: [Text content of criteria chunk]`
* **Metadata Fields (Strict JSON Property Schema):**
  ```json
  {
    "trial_id": "string (NCT-ID Reference matching SQLite Exactly)",
    "criterion_type": "string ('INCLUSION' | 'EXCLUSION')"
  }
  ```

### Index C: `icd11_taxonomy_embeddings`
* **Purpose:** Resolves colloquial user phrases to official alphanumeric medical terminology via proximity matches.
* **Document Vector String Template:** `Path: [Lineage Path] | Code: [icd11_code] | Label: [Title] | Definitions: [Description]`
* **Metadata Fields (Strict JSON Property Schema):**
  ```json
  {
    "icd11_code": "string (Primary Key reference matching SQLite Exactly)",
    "title": "string (Official categorization label name)",
    "chapter_root": "string (Top level code grouping tracking descriptor)"
  }
  ```

### Index D: `semantic_llm_cache`
* **Purpose:** Enterprise-grade edge short-circuit layer to save token budget. Prevents duplicate LLM invocation for identically-worded inputs.
* **Document Vector String Template:** `[Fully-scrubbed, normalized patient ingress clinical text string]`
* **Metadata Fields (Strict JSON Property Schema):**
  ```json
  {
    "cached_case_id": "string (UUIDv4 reference of origin case output)",
    "extracted_codes_json": "string (Serialized Array of codes e.g. '[\"1A40\", \"1B11\"]')"
  }
  ```

---

## ⚡ 3. RUNTIME DISTRIBUTED STATE CONTROL LAYER (Upstash Redis)

*Purpose: Enforces absolute operational limits and prevents system-wide provider failures across auto-scaling server environments.*

### Keyspace A: Global Token/Request Rate Limiter
* **Key ID Pattern:** `rate_limit:groq_api_gate`
* **Data Core Type:** String (Atomic Integer Counter acting as an isolated Fixed-Window Limit)
* **Value Behavior Constraints:** Decremented automatically via runtime pipeline calls before calling an external AI endpoint. If value $\le 0$, newly arriving requests pause execution, preventing upstream `429 Rate Limit Errors`.

### Keyspace B: Thread Execution Mutex (Distributed Lock Engine)
* **Key ID Pattern:** `lock:case_id:{case_id_string}`
* **Data Core Type:** String (Value = Active Processing Server Worker ID Token)
* **Storage Operational Constraints:** Applied with an absolute short-duration `EXPIRE` duration TTL window (e.g., 60 seconds). Prevents double-processing race conditions across horizontal server environments if an end-user double-clicks execution or a serverless worker restarts unexpectedly.

[Tier 1: Base Tables] ---------> [Tier 2: Core Records] ---------> [Tier 3: Junctions & Logs]
- Patient_identity_vault          - Patient_cases                 - Patient_extracted_codes
- ICD11_taxonomy_reference                                        - Trial_Target_codes
- Clinical_trial                                                  - Trial_Matches
                                                                  - Human_Review_Logs