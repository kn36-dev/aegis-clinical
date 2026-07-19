# aegis-clinical 🛡️

## Deterministic AI Orchestration for Clinical Note Structuring

`aegis-clinical` is a reference architecture demonstrating how modern AI systems can safely transform unstructured clinical notes into structured ICD-11 classifications through deterministic workflow orchestration, semantic retrieval, and human-in-the-loop validation.

Rather than relying on autonomous agent loops, the system combines explicit state-machine orchestration with bounded AI reasoning to ensure every clinical note follows a deterministic execution path from ingestion through physician approval. The repository emphasizes architectural correctness, clear data ownership, reproducible execution, and evaluation-driven development over infrastructure scale.

---

# Architectural Overview

The application is intentionally organized around clear responsibility boundaries, where every major component owns exactly one concern.

### LangGraph — Deterministic Workflow Orchestration

LangGraph acts as the macro-orchestrator of the application. It defines the immutable execution topology responsible for sequencing data anonymization, semantic retrieval, AI-assisted reasoning, physician review, persistence, and workflow resumption. Human-in-the-Loop (HITL) checkpoints suspend execution safely until physician approval before allowing downstream state transitions.

### CrewAI — Bounded Clinical Reasoning

CrewAI encapsulates the clinical reasoning boundary. The v1 implementation intentionally uses a **single specialist reasoning agent** that interprets the anonymized note against the semantically retrieved ICD-11 candidates and produces a structured coding recommendation. The point of the boundary is not agent count — it is to keep reasoning cleanly separable from orchestration, so additional specialist agents (symptom extraction, negation/context analysis, temporal reasoning) can be added later without touching the LangGraph state machine. Agent execution stays isolated inside deterministic workflow boundaries and never controls application flow. See `docs/crewAI_architectural_decision.md`.

### Pydantic — Structured Validation Boundary

All AI-generated outputs pass through strongly typed **Pydantic** models before entering the application domain. This boundary converts probabilistic language-model responses into deterministic application objects while rejecting malformed, incomplete, or semantically invalid outputs before they reach persistence layers.

> **Future v2 exploration:** [PydanticAI](https://ai.pydantic.dev/) may be introduced for stronger typed agent/tool boundaries and structured agent execution. It is a declared dependency but is **not currently integrated** — v1 validation is plain Pydantic, and CrewAI remains the reasoning boundary. This is a future architectural evaluation, not a planned replacement of CrewAI.

---

# Storage Architecture

The persistence layer follows a strict separation of responsibilities.

### SQLite — System of Record

SQLite serves as the authoritative source of truth for all mutable application state, including clinical cases, physician-approved ICD-11 classifications, audit history, workflow checkpoints, optimistic versioning, and the complete ICD-11 taxonomy. Write-Ahead Logging (WAL) mode enables concurrent reads while preserving transactional consistency.

### Upstash Vector — Semantic Retrieval

A single Upstash Vector index contains a read-only `taxonomy_lookup` namespace populated with precomputed embeddings of the official ICD-11 taxonomy. The current default embedding provider is **SentenceTransformers `BAAI/bge-large-en-v1.5` (1024-dimensional)**; because embedding providers sit behind a swappable interface (`src/aegis/embeddings/`), OpenAI's `text-embedding-3-small` (1536-dimensional) can be selected instead via `EMBEDDING_*` settings without changing retrieval logic.

The vector database functions exclusively as a semantic nearest-neighbor index, returning ICD-11 identifiers during similarity search. Clinical descriptions, taxonomy metadata, and application state remain solely within SQLite, following a pointer-based architecture that avoids duplicated mutable data across storage systems.

### Upstash Redis — Deterministic Cache

Redis provides an exact-match cache keyed by the SHA-256 hash of normalized clinical notes. Previously processed notes bypass semantic retrieval and AI reasoning entirely, returning physician-approved ICD-11 classifications with zero additional embedding generation or LLM inference cost. This deterministic cache improves efficiency over time while preserving SQLite as the authoritative data source.

---

# Clinical Processing Pipeline

Every clinical note progresses through a deterministic execution pipeline:

1. PHI anonymization and normalization.
2. Deterministic Redis cache lookup using the normalized note hash.
3. Semantic retrieval of candidate ICD-11 codes from Upstash Vector upon cache miss.
4. Bounded AI-assisted reasoning through a single CrewAI clinical reasoning agent.
5. Structured validation via Pydantic schemas.
6. Human-in-the-Loop physician approval.
7. Transactional persistence into SQLite.
8. Deterministic Redis cache update for future identical requests.

This architecture intentionally combines deterministic state transitions with bounded AI reasoning, ensuring that probabilistic model outputs never directly control workflow execution.

---

# Repository Structure

```text
aegis-clinical/
├── data/                        # ICD-11 CSV, seeded SQLite DBs, fixtures
├── docs/                        # Reader-facing architecture docs (+ docs/history/)
├── evals/                       # AI-quality eval dataset + harness (clinical_cases.jsonl)
├── config/                      # evaluation.yaml / evaluation.production.yaml
├── runtime_domain_contracts/    # Authoritative runtime domain contracts
├── application_service_contracts/  # Authoritative application service contracts
├── frontend/                    # React 19 + Vite physician dashboard (feature-based)
├── src/
│   └── aegis/
│       ├── agents/              # CrewAI reasoning agent(s)
│       ├── api/                 # FastAPI app, routers, bootstrap composition root
│       ├── database/            # SQLite migrations, connection, repositories, CLI
│       ├── embeddings/          # Swappable embedding providers (BGE / OpenAI)
│       ├── vectorstores/        # Vector store abstraction (local / Upstash)
│       ├── indexing/            # Offline knowledge-compilation pipeline (Phase 1)
│       ├── retrieval/           # Runtime retrieval preparation (Phase 2)
│       ├── services/            # Deterministic application services
│       ├── graphs/              # LangGraph workflow, nodes, state, checkpointing
│       ├── schemas/             # Pydantic structured-output validation
│       ├── prompts/             # Versioned reasoning prompt assets
│       ├── evaluation/          # Custom deterministic eval framework (aegis-eval)
│       └── infrastructure/      # SQLite / Redis / CrewAI adapters
├── tests/                       # Deterministic software-correctness tests
├── pyproject.toml
└── README.md
```

> Note: `.github/workflows/lint_and_typecheck.yml` exists but is currently empty — CI is not yet enforcing the quality gate. The `providers/` package is an orphaned earlier LLM-provider abstraction with no current callers.

---

# Verification Strategy

The repository distinguishes functional correctness from AI quality evaluation.

## Unit Tests

Verify deterministic business logic, schema validation, state transitions, and utility functions independent of external AI providers.

## Integration Tests

Validate complete workflow execution across orchestration, persistence, checkpointing, and Human-in-the-Loop interactions using synthetic datasets.

## Evaluation Framework

AI-quality evaluation is maintained independently from traditional software tests. AEGIS ships a **custom deterministic evaluation framework** (`src/aegis/evaluation/`, CLI: `aegis-eval`, dataset: `evals/clinical_cases.jsonl`, config-driven via `config/evaluation.yaml`) that reuses the same real application services the production workflow uses. It measures two boundaries:

- **Retrieval quality** — Recall@K, Hit Rate@K, and Mean Reciprocal Rank against a curated ICD-11 fixture (`local`) or the real Upstash Vector index (`production`).
- **Reasoning quality** — deterministic scoring only (no LLM-as-judge yet): schema validity, expected-code alignment, and evidence grounding.

Every run writes reproducible, provenance-stamped reports (git commit, dataset hash, config hash, model/provider) under `.artifacts/evaluations/`. See `docs/testing_and_evaluations.md` for the full methodology and the deferred roadmap (LLM-as-judge, Braintrust experiment tracking — both future, not yet integrated).

---

# Running the Demo (Real Retrieval, Minimal Credentials)

A complete, reproducible run of the clinical pipeline — submission, AI-assisted recommendation, physician review, and persisted decision — is available as a single command:

```bash
make db-init && make db-seed-icd   # once, before the first run
make demo
# equivalent to: AEGIS_PROFILE=demo uv run python scripts/demo_e2e.py
```

This drives the real FastAPI application (`aegis.api.main.app`) through its HTTP boundary using FastAPI's `TestClient` — the real lifespan, the real LangGraph workflow, and the real interrupt/resume suspension all run exactly as they would under `make dev-backend`, against the same composition root (`aegis/api/bootstrap.py`) and the same real, locally-seeded `data/clinical_registry.db` that `make demo-server` below uses. Under `AEGIS_PROFILE=demo`, embedding and Upstash Vector retrieval stay real (see "Running the Demo Server" below for why); only the cache, reasoning, and content-repository collaborators are deterministic in-memory substitutes. That means `make demo` needs `UPSTASH_VECTOR_REST_URL`/`UPSTASH_VECTOR_REST_TOKEN` and the `EMBEDDING_*` settings in `.env`, but not `GROQ_API_KEY` or Upstash Redis credentials. Because retrieval is real, the physician's decision in the script is read back from whatever the AI actually recommended, not a hardcoded ICD code.

A second, credential-free scenario is expressed as an automated test in `tests/integration/test_clinical_pipeline.py` (fake embedding/retrieval too, ephemeral SQLite, no `.env` needed), including the cache-hit path on a repeat submission:

```bash
uv run pytest tests/integration/test_clinical_pipeline.py -v
```

`make integration` runs the identical script (`scripts/integration_e2e.py`, sharing its workflow logic with `scripts/demo_e2e.py` via `scripts/e2e_common.py`) under `AEGIS_PROFILE=integration` instead: real Redis-backed cache and real CrewAI/Groq reasoning replace demo's in-memory ones, so it also needs `GROQ_API_KEY` and the Upstash Redis credentials. Its purpose is verifying that the full external infrastructure wiring works, not exercising different application logic.

See `docs/tradeoffs_and_limitations.md` — "Live-Credential Content Seeding Gap" — for why both `make demo` and `make integration` submit one of a fixed set of pre-seeded sample notes rather than arbitrary freshly-typed text.

---

# Running the Demo Server (React Frontend, One Real Credential)

The script above is a fully offline, zero-credential *reproduction* of the pipeline. There is a second, distinct way to run the demo: a real, long-lived FastAPI server the React frontend (`frontend/`) talks to over HTTP, which is what a live interview walkthrough actually uses.

It is the exact same application — same FastAPI app, same routers, same LangGraph workflow, same application services — started with one configuration value changed:

```bash
AEGIS_PROFILE=demo make demo-server
# equivalent to: AEGIS_PROFILE=demo uv run uvicorn aegis.api.main:app --app-dir src --reload --port 9000
```

`AEGIS_PROFILE=demo` changes only which collaborators `aegis/api/bootstrap.py` (the composition root) assembles:

- **Real, unchanged:** SQLite persistence, the full ICD-11 taxonomy, PHI anonymization/normalization, the embedding provider, and Upstash Vector retrieval — this profile queries the actual ~15,000-vector BGE-large index the offline indexing pipeline built, so the retrieval results a reviewer sees are genuinely real.
- **Deterministic substitutes:** the cache (in-memory instead of Upstash Redis), clinical reasoning (a deterministic adapter that recommends the top real retrieval candidate instead of calling Groq/CrewAI — see `DeterministicTopCandidateReasoningProvider`), and the content repository (in-memory, pre-seeded with a fixed set of sample notes, for the same reason described below).

This means the server needs only `UPSTASH_VECTOR_REST_URL`/`UPSTASH_VECTOR_REST_TOKEN` and the `EMBEDDING_*` settings from `.env` — no `GROQ_API_KEY` or Upstash Redis credentials.

Submissions in this profile must use one of the pre-seeded `content_reference` values in `aegis.api.bootstrap.DEMO_SAMPLE_NOTES` (the frontend is expected to offer these as selectable sample cases), not arbitrary freshly-typed text — see "Live-Credential Content Seeding Gap" below for why.

---

# Engineering Principles

The architecture is guided by several core design principles:

* Deterministic workflow execution over autonomous agent control.
* Single source of truth for all mutable application state.
* Explicit separation between orchestration, reasoning, validation, and persistence.
* Pointer-based semantic retrieval without duplicated mutable metadata.
* Evaluation-driven AI development with reproducible benchmarks.
* Minimal infrastructure complexity while preserving clear production evolution paths.
