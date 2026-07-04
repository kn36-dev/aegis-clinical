# How the Aegis database layer works exactly

This document is the canonical mental model for the SQLite-backed persistence layer in this repository. It explains what exists, why it exists, how the data is organized, and how the code initializes and uses it.

## 1. Executive summary

The database layer is split into two SQLite databases:

- Clinical database: used for patient, case, ICD, trial, and review data.
- Graph/state database: used for LangGraph checkpoint state and workflow resumption.

The implementation is intentionally simple and explicit:

- SQLite is the storage engine.
- Migrations are applied in order and are idempotent.
- Each database is initialized through a small set of Python entry points.
- Foreign keys are enabled.
- WAL mode is used for better concurrency behavior.

The design is optimized for clarity and reproducibility rather than for enterprise-scale multi-tenant deployment.

## 2. Where the database layer lives

The main database package is:

- [src/aegis/database](src/aegis/database)

The most important implementation files are:

- [src/aegis/database/database.py](src/aegis/database/database.py): schema initialization and database status helpers
- [src/aegis/database/connection.py](src/aegis/database/connection.py): SQLite connection wrapper and PRAGMA settings
- [src/aegis/database/cli.py](src/aegis/database/cli.py): command-line entry points
- [src/aegis/database/seeds.py](src/aegis/database/seeds.py): CSV/JSON ingestion into the clinical schema
- [src/aegis/database/migration](src/aegis/database/migration): ordered SQL migration files

## 3. The two databases and their purpose

### 3.1 Clinical database

Default path:

- data/clinical_registry.db

This database stores the domain data for the clinical pipeline:

- patient identities
- patient clinical cases
- ICD-11 taxonomy reference data
- extracted medical codes from cases
- clinical trial definitions
- trial matching outcomes
- human review decisions

### 3.2 Graph/state database

Default path:

- data/graph_state.db

This database stores workflow checkpoint blobs for LangGraph-style orchestration. Its purpose is not clinical reasoning but workflow state persistence and resumption.

## 4. Schema initialization flow

The initialization flow is straightforward:

1. The code chooses the target database path.
2. It opens a SQLite connection through the shared connection wrapper.
3. It runs the ordered migration scripts.
4. It commits the schema.

The key functions are:

- init_clinical_database()
- init_graph_database()
- init_all_databases()

The migration order is:

- clinical database:
  - 0001_init_patient_identity_vault
  - 0002_init_patient_case
  - 0003_init_icd11_taxonomy_reference
  - 0004_init_patient_extracted_code
  - 0005_init_clinical_trial
  - 0006_init_trial_target_code
  - 0007_init_trial_match
  - 0008_init_human_review_log

- graph database:
  - 0001_init_checkpoint_blob

## 5. Connection behavior

Every SQLite connection is configured with the same safety and performance pragmas:

- WAL mode
- busy_timeout = 30000
- synchronous = NORMAL
- foreign_keys = ON

This makes the database layer more robust for repeated writes and avoids accidental violations of referential integrity.

## 6. Tables in the clinical database

The clinical database contains the following core tables.

### 6.1 patient_identity_vault

Purpose:

- Stores the canonical identity record for a patient.
- Supports de-identification and HIPAA-conscious handling.

Columns:

- patient_id: primary key; stable identifier for the patient
- medical_record_number: unique, required; used as a non-PII identifier source
- first_name: required; stored as part of the identity envelope
- last_name: required
- date_of_birth: required

Why it exists:

- It is the root identity table.
- Other tables reference it via patient_id.

### 6.2 patient_case

Purpose:

- Represents a single clinical case or ingestion event for a patient.
- Tracks the lifecycle of case processing.

Columns:

- case_id: primary key; unique case identifier
- patient_id: foreign key to patient_identity_vault(patient_id)
- thread_id: unique workflow thread identifier for LangGraph resumption
- status: current workflow state of the case
- ingress_timestamp: time the case entered the system
- raw_clinical_note: the original note as ingested
- anonymized_clinical_note: optionally sanitized version of the note
- version: optimistic concurrency or revision marker

Important notes:

- Each patient can have multiple cases.
- Each case has a dedicated workflow thread, which is used to tie the case to the graph/checkpoint system.
- The design is meant to support human-in-the-loop review and reprocessing.

### 6.3 icd11_taxonomy_reference

Purpose:

- Stores a canonical ICD-11 taxonomy reference table.
- Acts as the medical code dictionary used by the rest of the system.

Columns:

- code: primary key; ICD-11 code
- title: human-readable title
- class_kind: classification category
- context_path: breadcrumb-style path for hierarchical context

Why it exists:

- The rest of the pipeline uses this as the authoritative code vocabulary.
- It prevents free-form code values from drifting across ingestion, matching, and review logic.

### 6.4 patient_extracted_code

Purpose:

- Stores the ICD-11 codes extracted from a specific case.
- Represents a many-to-many relationship between a case and extracted medical codes.

Columns:

- case_id: part of composite primary key; references patient_case(case_id)
- icd11_code: part of composite primary key; references icd11_taxonomy_reference(code)
- confidence_score: numeric confidence score between 0.0 and 1.0
- extraction_source: indicates whether the code came from an AI model, physician review, or another source

Important notes:

- One case can have many extracted codes.
- One code can be assigned to many cases.
- This is a join table with payload.

### 6.5 clinical_trial

Purpose:

- Stores trial metadata.

Columns:

- trial_id: primary key
- title: human-readable trial name
- phase: trial phase
- sponsor: sponsor organization
- status: recruitment state
- raw_eligibility_criteria: source text used for semantic matching

Why it exists:

- Trial matching is a first-class function of the system.
- The trial table is a canonical catalog of available study opportunities.

### 6.6 trial_target_code

Purpose:

- Maps a clinical trial to the ICD-11 codes that are relevant to its inclusion or exclusion criteria.

Columns:

- trial_id: part of composite primary key; references clinical_trial(trial_id)
- icd11_code: part of composite primary key; references icd11_taxonomy_reference(code)
- criterion_type: either INCLUSION or EXCLUSION

Important notes:

- This table makes trial eligibility logic explicit in the database.
- The schema is designed so the matching engine can compare patient-diagnosis profiles against trial inclusion and exclusion criteria.

### 6.7 trial_match

Purpose:

- Stores the outcome of matching a patient case to a clinical trial.

Columns:

- match_id: primary key
- patient_id: foreign key to patient_identity_vault(patient_id)
- trigger_case_id: the case that caused the match to be generated
- trial_id: foreign key to clinical_trial(trial_id)
- structural_match_score: numeric match confidence score between 0 and 1
- match_status: review state of the match
- justification_summary: explanation of why the match was proposed
- created_at: timestamp of the match event

Important notes:

- A patient can be matched to multiple trials.
- The same patient and trial pair is constrained to be unique.
- This table is the bridge between clinical reasoning and human review.

### 6.8 human_review_log

Purpose:

- Records physician or reviewer actions for auditability.

Columns:

- review_id: primary key
- case_id: foreign key to patient_case(case_id)
- reviewer_badge_id: identifier for the reviewer
- action_taken: one of the allowed review actions
- physician_notes: optional free-text rationale
- cryptographic_signature: integrity marker for the review event
- timestamp: event time

Why it exists:

- The system is designed to support human-in-the-loop oversight.
- This table preserves a tamper-evident audit trail.

## 7. Table in the graph/state database

### 7.1 checkpoint_blob

Purpose:

- Stores serialized workflow state checkpoints for the graph engine.

Columns:

- thread_id: part of composite primary key
- checkpoint_id: part of composite primary key
- parent_id: references the previous checkpoint in the chain
- checkpoint: binary blob containing the workflow state payload
- metadata: binary blob containing trace or execution metadata

Why it exists:

- It allows workflow resumption and deterministic replay.
- It keeps graph orchestration state separate from clinical domain data.

## 8. Relational architecture

The architecture is a classic relational model with a small number of key relationships.

### 8.1 Identity and case flow

- One patient in patient_identity_vault can have many patient_case records.
- Each patient_case belongs to exactly one patient.

This is the core patient-case hierarchy.

### 8.2 Case and extracted codes

- One patient_case can have many patient_extracted_code rows.
- Each patient_extracted_code belongs to one case and one ICD-11 code.

This makes case-level diagnostic outputs explicit and queryable.

### 8.3 Case and review history

- One patient_case can have many human_review_log entries.
- Each review log belongs to exactly one case.

This supports audit and physician review workflows.

### 8.4 Trial and code criteria

- One clinical_trial can have many trial_target_code rows.
- Each trial_target_code row belongs to one trial and one ICD-11 code.

This creates an explicit eligibility ontology for cohort matching.

### 8.5 Patient and trial matching

- One patient can have many trial_match rows.
- One case can trigger many trial_match rows.
- One trial can be matched to many patients.

This is the operational matching layer between patient profiles and trial eligibility.

### 8.6 ICD taxonomy as a shared reference backbone

The icd11_taxonomy_reference table is the shared reference dictionary used by both:

- patient_extracted_code
- trial_target_code

This makes the data model consistent across case extraction and trial matching.

## 9. Why the database is split into two files

The system uses two different persistence concerns:

- clinical and review data: stable domain records
- graph execution state: ephemeral and workflow-oriented state

Keeping them separate improves clarity and avoids mixing workflow internals with business data. It also makes it easier to rebuild or reset one part of the system without destroying the other.

## 10. Important implementation details

### 10.1 Migrations are ordered and idempotent

The SQL files are designed to be applied repeatedly without breaking. Each migration uses CREATE TABLE IF NOT EXISTS.

### 10.2 The schema is intentionally simple

The current architecture uses SQLite rather than a heavier relational engine because the project is designed for local development, demonstration, and evaluation use.

### 10.3 Referential integrity is on

The connection layer enables foreign key enforcement, so the database rejects invalid references when possible.

### 10.4 The system uses a small CLI layer

The CLI supports:

- scaffold
- init
- seed
- status

This gives the project a reproducible database bootstrap story.

### 10.5 Seed data is imported from local files

The seeding layer loads:

- ICD-11 taxonomy data from a CSV file
- mock clinical case data from a JSON file

These seed operations populate the clinical schema with realistic example data.

## 11. One important architectural nuance

There is a slight implementation split between the migration-based schema and the repository helper layer:

- The migration files define the canonical schema used by the database initialization path.
- Some repository-oriented Python modules contain simplified or compatibility-oriented logic.

For the purpose of understanding the system architecture, the migration files and the database initialization layer are the most reliable source of truth.

## 12. Mental model for another LLM

If you need to reason about the system quickly, use this shorthand:

- patient_identity_vault = who the patient is
- patient_case = what clinical case the patient has
- icd11_taxonomy_reference = the medical code dictionary
- patient_extracted_code = which codes were extracted from each case
- clinical_trial = what trials exist
- trial_target_code = which codes matter for each trial
- trial_match = which trial matched which patient case
- human_review_log = what the reviewer did
- checkpoint_blob = how the workflow state is saved for resumption

That is the core of the architecture.

## 13. Bottom line

The database layer is a compact, relational, SQLite-based persistence layer that supports:

- patient and case management
- medical code normalization
- trial matching
- physician review and auditability
- workflow checkpointing for graph execution

It is deliberately simple, explicit, and easy to inspect. The main architectural decision was to keep domain data and workflow state separate while still linking them through case identifiers and workflow thread identifiers.
