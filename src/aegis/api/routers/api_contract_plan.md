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
│   ├── errors.py
│   ├── identity.py
│   ├── patient.py
│   ├── review.py
│   └── trial.py
└── routers/
    ├── clinical.py
    ├── patient.py
    ├── review.py
    ├── trial.py
    ├── workflow.py
    └── demo.py

## Wiring status (what `main.py` actually includes)

Only four routers are registered in `aegis.api.main`:

- **clinical** — `POST /api/v1/clinical-notes` (§1). **Wired.**
- **review** — `GET`/`POST /api/v1/reviews/{thread_id}[/decision]` (§3). **Wired.**
- **workflow** — `GET /api/v1/workflows/...` (§5, workflow observability). **Wired.**
- **demo** — `GET /api/v1/demo/patients` (returns the pre-seeded demo patients used by the
  demo profile). **Wired.** Not otherwise documented in this plan.

The **patient** (§2) and **trial** (§4) routers exist as files but are **not** included in
`main.py` — they are scaffolding for future capability (patient workspace and clinical
trial matching, both Future v2), not live endpoints today.

---

# 1. Clinical Processing

Responsible for starting AI-powered clinical note ingestion.

## POST /api/v1/clinical-notes (implemented -- Slice 1)

Purpose

Starts a brand-new LangGraph workflow for processing a physician's clinical note.

Input

- patient_id
- content_reference

Workflow

Create WorkflowState

↓

Normalize clinical note

↓

Redis deterministic cache lookup

↓

(Cache Hit?)
    ├── Yes → Return cached ClinicalDecision, status=completed
    └── No

↓

Generate embedding

↓

ICD-11 taxonomy semantic retrieval

↓

CrewAI clinical reasoning

↓

Pause for Human Review (LangGraph interrupt), status=pending_review

Returns

- workflow_id (LangGraph checkpoint thread id)
- case_id
- status (pending_review | completed)
- decision_id, approved_icd_codes (only when status=completed)

Resuming a pending_review workflow is
GET/POST /api/v1/reviews/{thread_id}[/decision] (`workflow_id` returned here
*is* that `thread_id`) -- out of scope for Slice 1, implemented in Slice 2.
See "3. Human-in-the-Loop (HITL)" below.

---

# 2. Patient Workspace

> **Status: not implemented (Future v2 scaffold).** The `patient` router is not wired into
> `main.py`. The endpoints below are a plan, not live routes.

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

**Current contract (implemented -- Slice 2)** is the LangGraph
interrupt/resume boundary below. The `review_id`-keyed,
`/approve`/`/reject`/`/amend`-shaped design further down this section
was the pre-Slice-2 plan and is superseded -- see "Historical / deprecated
design" for why it was never built as written and what, if anything, of
it still applies.

## GET /api/v1/reviews/{thread_id} (implemented -- Slice 2)

Purpose

Retrieve the current pending-or-completed review state for a workflow,
identified by its LangGraph checkpoint `thread_id` (the same id returned
as `workflow_id` by `POST /api/v1/clinical-notes`) -- there is no separate
`review_id`; the workflow's own thread id is the review's identity.

Workflow

`graph.aget_state(thread_id)`

↓

Empty snapshot → 404 (no workflow for that thread)

↓

`clinical_decision` present → status=completed

↓

Pending interrupt → status=pending_review

Returns

- workflow_id, case_id, status (pending_review | completed)
- when pending_review: recommendation_id, reasoning_summary,
  normalized_note_text (anonymized), recommended_icd_codes
  (icd_code, justification, model_confidence, supporting/conflicting findings)
- when completed: decision_id, approved_icd_codes

The router only reads already-computed workflow state here -- it performs
no ICD validation, no approval classification, and constructs no
`ClinicalDecision`. See `aegis.api.routers.review`.

---

## POST /api/v1/reviews/{thread_id}/decision (implemented -- Slice 2)

Purpose

Submit the physician's final set of approved ICD-11 codes and resume the
LangGraph workflow suspended at `human_review_pending`.

Input

- selected_icd_codes (only the physician's final code list; no
  accept/reject/amend distinction is made by the request or the router --
  see below)

Workflow

`graph.aget_state(thread_id)` to read case/recommendation/patient/
normalization identity out of the workflow's own suspended state (never
trusted from the request)

↓

Build `PhysicianDecisionSubmission` (identity from state + codes from the
request)

↓

`graph.ainvoke(Command(resume=submission))`

↓

Graph resumes: `decide_case` (`ClinicalDecisionService`) → classifies each
code accepted/added/removed/modified → `persist_clinical_decision`
(`PersistenceService`, SQLite) → `cache_store` (Redis) → END

Returns

- workflow_id, case_id, decision_id, approved_icd_codes (each with its
  disposition, as classified by `ClinicalDecisionService`)

**What the router does not do:** classify ACCEPTED vs. ADDED vs. REMOVED
vs. MODIFIED, call `ClinicalDecisionService`/`PersistenceService`
directly, or persist/cache anything itself. There is also no separate
`/approve`, `/reject`, or `/amend` endpoint -- a single `selected_icd_codes`
list covers all three cases, and the graph (not the router) determines
each code's disposition. See `aegis.api.routers.review`.

---

## Historical / deprecated design (pre-Slice 2 -- not implemented as written)

The plan below predates the LangGraph interrupt/resume boundary being
wired up and assumed a `review_id`-keyed resource with separate
`/approve`, `/reject`, `/amend` actions and its own "pending reviews list"
endpoint. None of this was ever built this way, and it should not be read
as describing current or planned-next behavior -- the actual review
identity is the workflow's own `thread_id`, and approve/reject/amend
collapse into the single `selected_icd_codes` payload above, since that
classification is `ClinicalDecisionService`'s job, not the router's.

`GET /api/v1/review/pending` (a list of all pending reviews across
workflows) is a genuinely distinct capability nothing above provides --
it would require enumerating checkpoints across threads, not resuming
one. If a "review inbox" is wanted later, it belongs to whichever slice
introduces workflow enumeration/listing (see "5. Workflow Monitoring"
below, which has the same gap for `GET /api/v1/workflows/{workflow_id}`
singular lookup vs. listing) -- it is out of scope for, and not a gap in,
Slice 2's interrupt/resume boundary.

~~GET /api/v1/review/pending~~
~~GET /api/v1/review/{review_id}~~
~~POST /api/v1/review/{review_id}/approve~~
~~POST /api/v1/review/{review_id}/reject~~
~~POST /api/v1/review/{review_id}/amend~~

---

# Identity Boundary (implemented -- Slice 4)

Purpose

Give caller identity (physician, institution, ...) a defined place to
enter AEGIS from HTTP, without building authentication, authorization,
or user management. Routers should never read `Request`/headers
directly to determine "who is calling"; they depend on
`get_identity_context` instead.

```
HTTP
  ↓
Identity Context Adapter   (aegis.api.dependencies.get_identity_context)
  ↓
RequestIdentityContext     (aegis.api.schemas.identity)
  ↓
Future Authorization / Audit
```

Implemented

- `RequestIdentityContext` (`actor_id`, `actor_type`,
  `institution_reference`, all optional) -- the DTO identity is carried
  in at the API boundary.
- `get_identity_context(request)` -- a FastAPI dependency that relays
  whatever a future authentication adapter has attached to
  `request.state.identity_context`; it never reads headers/cookies/
  tokens itself and never fabricates a default actor.
- `POST /api/v1/clinical-notes`, `GET /api/v1/reviews/{thread_id}`, and
  `POST /api/v1/reviews/{thread_id}/decision` all accept
  `identity: RequestIdentityContext = Depends(get_identity_context)`.

Not implemented (deliberately out of scope for this slice)

- Authentication (no OAuth, JWT validation, SSO, or external identity
  provider).
- Authorization (no `can_approve()`, `is_physician()`, permission
  checks, or RBAC engine).
- Threading identity into `ClinicalNoteSubmission`,
  `PhysicianDecisionSubmission`, `AegisWorkflowState`, or
  `ClinicalDecision` -- none of those runtime domain contracts define
  an actor/institution field today (see
  `runtime_domain_contracts/clinical_decision.md`'s Identity section),
  and adding one is a contract change outside this slice's scope.
- Any audit trail construction or persistence.

Until a real authentication adapter exists, every request resolves to
an all-`None` `RequestIdentityContext` -- read as "identity not yet
established," not as "anonymous" or "unauthorized." No claim of secure
authentication, HIPAA compliance, or equivalent is made by this
boundary.

---

# 4. Clinical Trial Management

> **Status: not implemented (Future v2 scaffold).** The `trial` router is not wired into
> `main.py`, and clinical trial matching is a documented Future v2 capability. The
> endpoints below are a plan, not live routes.

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

> **Status: router wired** at prefix `/api/v1/workflows` (v1 observability). Confirm exact
> path/response shape against `aegis.api.routers.workflow`; the sketch below predates the
> implementation. Singular-lookup vs. cross-thread listing has the same enumeration gap
> noted for the "review inbox" in §3.

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

## GET /health (implemented)

Purpose

Lightweight readiness probe. Verifies only that the application booted, the DI container
was assembled, and the graph compiled -- no SQLite/Redis/Upstash/LLM connectivity checks
(those are enforced at startup before the app accepts traffic). Note the real path is
`/health` (root), not `/api/v1/health`.

Returns (`dict[str, bool]`, see `aegis.api.main.health_check`)

- booted
- container_ready
- graph_ready

Example

{
    "booted": true,
    "container_ready": true,
    "graph_ready": true
}

> The earlier `{status, engine, security: "HIPAA Guarded"}` shape was never implemented and
> made no HIPAA claim in the real system -- see the identity-boundary note above: AEGIS
> makes no claim of secure authentication or HIPAA compliance.

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