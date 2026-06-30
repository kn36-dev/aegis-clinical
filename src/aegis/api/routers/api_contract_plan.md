# Aegis Clinical — FastAPI Endpoint Implementation Plan

The API is organized around four bounded contexts that mirror the application's domain model:

1. Clinical AI Processing
2. Patient Workspace
3. Human-in-the-Loop (HITL) Review
4. Clinical Trial Management

Each router owns a single responsibility and should never directly perform business logic. Instead, routers validate requests, invoke LangGraph workflows or repository methods, and return typed response models.

---

# Router Structure

src/aegis/api/

├── main.py
├── dependencies.py
├── schemas/
│   ├── clinical.py
│   ├── patient.py
│   ├── review.py
│   └── trial.py
└── routers/
    ├── clinical.py
    ├── patients.py
    ├── review.py
    └── trials.py

---

# 1. Clinical Processing

Responsible for starting AI-powered clinical note ingestion.

## POST /api/v1/clinical/ingest

Purpose

Starts a brand-new LangGraph workflow for processing a physician's clinical note.

Input

- patient_id
- physician_id
- raw_clinical_note

Workflow

Create WorkflowState

↓

Normalize clinical note

↓

Redis deterministic cache lookup

↓

(Cache Hit?)
    ├── Yes → Return cached result
    └── No

↓

Generate embedding

↓

ICD-11 taxonomy semantic retrieval

↓

CrewAI clinical reasoning

↓

Pause for Human Review

Returns

- workflow_id
- review_id
- workflow_status

Example Status

WAITING_FOR_REVIEW

---

# 2. Patient Workspace

Supports physician navigation and historical review.

## GET /api/v1/patients

Purpose

Returns a paginated searchable patient list.

Supports

- pagination
- search
- sorting

Returns

- patient_id
- MRN
- full_name
- date_of_birth

---

## GET /api/v1/patients/{patient_id}

Purpose

Returns a patient overview.

Returns

- demographics
- current diagnoses
- enrolled trials
- latest clinical activity

---

## GET /api/v1/patients/{patient_id}/timeline

Purpose

Displays the complete audit timeline for a patient.

Timeline

Patient

↓

Clinical Note

↓

AI Suggested ICD-11

↓

Physician Approved ICD-11

↓

Trial Eligibility

↓

Matched Clinical Trials

Returns

Chronological timeline events with timestamps and responsible clinician.

---

# 3. Human-in-the-Loop (HITL)

Allows physicians to review AI output before persistence.

## GET /api/v1/review/pending

Purpose

Returns all pending physician reviews.

Returns

- review_id
- patient
- physician
- creation timestamp
- workflow status

---

## GET /api/v1/review/{review_id}

Purpose

Returns every detail required for physician review.

Returns

- original note
- extracted findings
- suggested ICD-11 codes
- confidence values
- clinical reasoning summary

---

## POST /api/v1/review/{review_id}/approve

Purpose

Accepts the AI recommendation without modification.

Workflow

Resume paused LangGraph

↓

Persist SQLite

↓

Update Redis cache

↓

Finish workflow

Returns

Workflow completed successfully.

---

## POST /api/v1/review/{review_id}/reject

Purpose

Rejects the AI recommendation.

Workflow

Terminate workflow

↓

Record audit outcome

Returns

Workflow rejected.

---

## POST /api/v1/review/{review_id}/amend

Purpose

Allows physician edits before approval.

Input

- modified ICD-11 codes
- optional comments

Workflow

Resume LangGraph

↓

Persist amended codes

↓

Update deterministic Redis cache

↓

Complete workflow

Returns

Updated workflow status.

---

# 4. Clinical Trial Management

Used by researchers to manage eligibility studies.

## POST /api/v1/trials

Purpose

Creates a new clinical trial.

Input

- title
- description
- inclusion criteria
- exclusion criteria

Returns

- trial_id
- created_at

---

## GET /api/v1/trials

Purpose

Returns all trials.

Returns

Trial summaries.

---

## GET /api/v1/trials/{trial_id}

Purpose

Returns the full trial definition.

Returns

- metadata
- inclusion criteria
- exclusion criteria
- current matching statistics

---

## POST /api/v1/trials/{trial_id}/match

Purpose

Explicitly starts patient matching.

Workflow

Retrieve trial

↓

Evaluate every eligible patient

↓

Persist trial_matches

↓

Return matching summary

Returns

- patients evaluated
- matches found
- execution time

This endpoint intentionally requires manual triggering for the portfolio demonstration instead of introducing background schedulers.

---

## GET /api/v1/trials/{trial_id}/matches

Purpose

Returns every matched patient.

Returns

- patient
- eligibility status
- explanation
- matching timestamp

---

# 5. Workflow Monitoring

## GET /api/v1/workflows/{workflow_id}

Purpose

Allows inspection of LangGraph execution state.

Useful for

- debugging
- demonstrations
- observability

Returns

- workflow_id
- current node
- workflow status
- started_at
- updated_at

Example Statuses

- RUNNING
- WAITING_FOR_REVIEW
- COMPLETED
- REJECTED

---

# 6. Health Check

## GET /api/v1/health

Purpose

Simple application readiness endpoint.

Returns

- status
- engine
- security profile

Example

{
    "status": "healthy",
    "engine": "LangGraph Active",
    "security": "HIPAA Guarded"
}

---

# Overall Request Flow

React UI

↓

FastAPI Router

↓

Request Validation (Pydantic)

↓

LangGraph Workflow

↓

CrewAI Clinical Reasoning

↓

PydanticAI Structured Output

↓

SQLite Persistence

↓

Redis Cache Update

↓

Response DTO

↓

React UI