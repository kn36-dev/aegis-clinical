# AEGIS Clinical — Portfolio Description

**Deterministic AI Systems Engineering | LangGraph · CrewAI · Retrieval-First Architecture**

A reference architecture demonstrating how to safely transform unstructured clinical
notes into structured ICD-11 classifications, built around one principle:
**deterministic systems own workflow execution; probabilistic systems (LLMs) contribute
bounded reasoning inside explicit guardrails.** The application governs the AI; the AI
never owns the application.

## What it demonstrates (v1, implemented)

- **Deterministic orchestration (LangGraph).** An explicit, resumable state machine
  sequences anonymization, deterministic caching, semantic retrieval, bounded AI
  reasoning, human-in-the-loop physician sign-off, and transactional persistence.
  Control flow (cache hit/miss, interrupt/resume) is deterministic code — never driven
  by model output.
- **Bounded reasoning (CrewAI).** A single specialist clinical-reasoning agent compares
  the anonymized note against semantically retrieved ICD-11 candidates and may only
  select from those candidates — it never invents codes.
- **Retrieval-first pipeline.** SHA-256 exact-match Redis cache → embedding → Upstash
  Vector nearest-neighbor retrieval → deterministic context assembly → a single
  `ReasoningContext` handed to the LLM.
- **Structured validation (Pydantic).** All model output is validated into typed domain
  objects before it can enter the domain or reach persistence.
- **Human-in-the-loop.** Physician review gates persistence; only physician-approved
  decisions become institutional truth and seed the cache.
- **Custom deterministic evaluation framework** (`aegis-eval`): Recall@K, Hit Rate@K, MRR
  for retrieval; deterministic contract/alignment/evidence scoring for reasoning; with
  reproducible, provenance-stamped reports.
- **Workflow visibility.** API endpoints and a React physician dashboard expose live
  workflow stage/progress and the review queue.

## Storage ownership

SQLite is the single system of record (clinical registry + ICD-11 taxonomy). Upstash
Vector (semantic retrieval) and Redis (deterministic cache) are derived/optimization
layers, never authoritative. A pointer-based design keeps mutable clinical content in
SQLite only.

## Future roadmap (not yet implemented)

Clearly scoped as future exploration, not current capability:

- **AI-assisted clinical trial matching / eligibility parsing** — the original framing of
  this project; deferred as an additional reasoning pipeline beyond the primary note →
  ICD-11 objective.
- **PydanticAI** — stronger typed agent/tool boundaries (evaluation, not a CrewAI
  replacement).
- **Braintrust** — evaluation experiment tracking, dataset versioning, LLM-as-judge.
- **OpenTelemetry** — distributed tracing and span-level production telemetry.

## Deployability note

This is a local, single-instance reference implementation (SQLite + Upstash free tier).
It is straightforward to run locally and reproducibly, but it is **not** packaged for edge
deployment today: it depends on external Upstash Vector/Redis services and a hosted LLM
(Groq) for the full pipeline, and production concerns (encryption at rest, PHI key
management, RBAC, distributed coordination) are deliberately out of scope — see
`docs/tradeoffs_and_limitations.md`. An edge-oriented variant would need local vector
storage, a local embedding model (already supported via SentenceTransformers), a local
cache, and a local LLM, all of which the provider abstractions leave room for.
