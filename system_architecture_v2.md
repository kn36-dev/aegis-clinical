# Aegis Clinical — System Architecture V2

> Status: **v1 implementation.** This document describes the system as currently built.
> The authoritative design lives in the runtime domain contracts
> (`runtime_domain_contracts/`, `domain_contract_finalized.md`) and application service
> contracts (`application_service_contracts/`, `application_service_finalized.md`); this
> file is a reader-facing overview that links up to them. Items marked **Future v2** are
> roadmap, not current capability.

## 1. Executive Summary

- **Project goal.** Transform unstructured clinical notes into structured ICD-11
  classifications as a case study for production-grade AI systems engineering.
- **Core philosophy.** Deterministic systems own workflow execution; probabilistic
  systems contribute bounded reasoning inside explicit guardrails. The application
  governs the AI.
- **Architectural principles.** Single system of record (SQLite); derived optimization
  layers (Vector, Redis) are never authoritative; retrieval provides evidence, not
  diagnosis; the LLM chooses only from retrieved candidates; physician review creates
  truth; every boundary is independently testable and evaluable.

---

## 2. High-Level Architecture

- **System context.** React physician dashboard → FastAPI → LangGraph orchestration →
  deterministic application services → repositories / infrastructure adapters / CrewAI
  reasoning.
- **Major components.** Offline knowledge-compilation pipeline; deterministic runtime
  preparation (retrieval); bounded AI reasoning (CrewAI); human-in-the-loop review;
  persistence.
- **End-to-end data flow.** `ClinicalNoteSubmission → ClinicalNote → NormalizedClinicalNote
  → (Redis cache lookup) → RetrievalResult → ReasoningContext → CodingRecommendation →
  physician review → ClinicalDecision → SQLite + Redis write-back`.

---

## 3. Canonical Domain Language

The runtime domain contracts are the architectural centre — every framework transforms,
validates, transports, or persists them. See `runtime_domain_contracts/`.

- **Business domain:** `ClinicalNote`, `ClinicalDecision`.
- **Processing artifacts:** `NormalizedClinicalNote`, `RetrievalRequest`,
  `RetrievalResult`, `ReasoningContext`, `CodingRecommendation`.
- **Workflow state:** `AegisWorkflowState` (`src/aegis/graphs/state.py`), the shared
  LangGraph state consolidated into domain-artifact fields.
- **Invariants:** contracts are immutable and framework-independent; similarity ≠
  confidence; recommendations never become truth; only `ClinicalDecision` triggers
  persistence and cache write-back.

---

## 4. Clinical Ingestion Pipeline

The wired LangGraph workflow (`src/aegis/graphs/workflow.py`):

1. `create_clinical_note` — `ClinicalNoteService`
2. `normalize_note` — `NormalizationService` (PHI anonymization + deterministic
   normalization)
3. `cache_lookup` — `CacheService` (SHA-256 exact-match Redis lookup)
4. **deterministic conditional edge** — cache hit → END (reuse prior `ClinicalDecision`);
   cache miss → continue
5. `retrieve_candidates` — `RetrievalService` (embedding + Upstash Vector)
6. `assemble_context` — `ContextAssembler` → `ReasoningContext`
7. `generate_recommendation` — `ClinicalReasoningService` (CrewAI) → `CodingRecommendation`
8. `human_review_pending` — LangGraph interrupt/resume boundary (no service)
9. `decide_case` — `ClinicalDecisionService` → `ClinicalDecision`
10. `persist_clinical_decision` — `PersistenceService` (SQLite)
11. `cache_store` — `CacheService` (Redis write-back) → END

> **v1 note:** the only conditional edge is the deterministic cache hit/miss route.
> Confidence-based auto-archiving of high-confidence cases is documented as a **Future v2**
> capability (`domain_contract_finalized.md`), not implemented.

---

## 5. Retrieval Architecture

- **Canonical ICD store (SQLite).** Authoritative ICD-11 taxonomy.
- **Representation Builder.** Title / Hierarchy / Prose text representations (single
  structured-prose baseline in v1; multi-representation is **Future v2**).
- **Embedding pipeline.** Default `BAAI/bge-large-en-v1.5` (1024-dim) via
  SentenceTransformers; OpenAI `text-embedding-3-small` (1536-dim) selectable behind the
  provider interface.
- **Upstash Vector.** Read-only `taxonomy_lookup` namespace returning ICD ids only
  (pointer-based; descriptions stay in SQLite).
- **Retrieval Service + candidate ranking.** Returns evidence only — no diagnosis, no
  clinical confidence.
- **Confidence gate.** **Future v2** — not implemented; all cache-miss cases route to
  human review today.

---

## 6. Prompt Engineering

- Versioned prompt assets live in `src/aegis/prompts/`, isolated from execution.
- Structured outputs are validated by Pydantic schemas (`src/aegis/schemas/`) before
  entering the domain.
- Prompt boundaries: the LLM sees curated candidates only, never similarity scores, and
  may only select from retrieved candidates.

---

## 7. LangGraph

- **Topology / nodes / transitions:** see §4.
- **Checkpointing:** `AsyncSqliteSaver` against `data/graph_checkpoints.db`, configured in
  the FastAPI lifespan (`src/aegis/api/main.py`). Interrupt/resume suspends ahead of
  physician review. Optimistic locking via a `version` column guards concurrency.

---

## 8. Repository Layer

- **SQLite** — system of record: clinical registry + ICD-11 taxonomy; schema via ordered
  migrations `0001`…`0012`.
- **Redis** — deterministic SHA-256 exact-match cache of physician-approved codes.
- **Upstash Vector** — semantic nearest-neighbor retrieval only.

---

## 9. Human-in-the-Loop

- **Review workflow.** Cache-miss cases suspend at `human_review_pending`; the physician
  reviews the anonymized note and recommended codes via the React dashboard.
- **Approval.** `POST /api/v1/reviews/{thread_id}/decision` submits the final code list;
  the graph (not the router) classifies each code's disposition and resumes.
- **Audit trail.** Persisted in SQLite (`human_review_log`, `clinical_decision`,
  `approved_icd_classification`).

---

## 10. Evaluation

Implemented as a custom deterministic framework (`src/aegis/evaluation/`, `aegis-eval`):

- **Retrieval metrics:** Recall@K, Hit Rate@K, MRR.
- **Reasoning metrics:** schema validity, expected-code alignment, evidence grounding
  (deterministic; no LLM-as-judge in v1).
- **Reproducibility:** provenance-stamped reports under `.artifacts/evaluations/`.

**Future v2:** LLM-as-judge, physician correction rate, Braintrust experiment tracking,
latency/cost telemetry (see `docs/testing_and_evaluations.md`).

---

## 11. Testing Strategy

Deterministic software correctness lives in `tests/` (schemas, repositories, migrations,
orchestration, integration). AI-quality evaluation lives in `evals/` + `aegis-eval` and
evolves independently. The two are kept deliberately separate.

---

## 12. Future Enhancements (v2 roadmap)

Not implemented today; documented as direction:

- Hybrid (dense + sparse) retrieval and multi-representation indexing.
- LLM-assisted re-ranking.
- Confidence-gated auto-archiving of high-confidence cases.
- AI-assisted clinical trial matching / eligibility parsing.
- **PydanticAI** for typed agent/tool boundaries (evaluation, not a CrewAI replacement).
- **Braintrust** evaluation platform (experiment tracking, dataset versioning, LLM-judge).
- **OpenTelemetry** distributed tracing and production telemetry.
- Institutional semantic memory (a second vector namespace over approved cases).
