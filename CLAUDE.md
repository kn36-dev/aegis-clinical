# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`aegis-clinical` is a **reference architecture / portfolio project**, not a shipping product. The clinical domain (transforming unstructured clinical notes into structured ICD-11 classifications) is a case study for demonstrating production-grade AI systems engineering. The intended reader is a hiring manager / principal engineer skimming for ~10 minutes. See `philosophies.md` and `README.md` for the full narrative.

The defining principle — reinforce it in every change:

> **Deterministic systems own workflow execution. Probabilistic systems (LLMs) contribute bounded reasoning inside explicit guardrails.** The application governs the AI; the AI never owns the application.

Consequences that constrain the code:
- CrewAI reasoning agents never touch infrastructure directly (no SQLite, Redis, Upstash Vector, or embedding-provider access from inside a reasoning agent). They receive a deterministic `ReasoningContext` and return structured output.
- Probabilistic model outputs never drive control flow. Routing (e.g. the cache-hit/miss edge in `graphs/workflow.py`) is deterministic code.
- SQLite is the single system of record; Redis and Upstash Vector are derived/optimization layers, never authoritative.

## Claude's Role

Claude Code operates here as an **implementation engineer working under an established architecture**, not as the system architect. The architecture is deliberate, documented in contracts, and substantially implemented.

What this means in practice:
- The **Runtime Domain Contracts** and **Application Service Contracts** are the authoritative design. Implement them faithfully rather than reinventing them.
- Preserve the architectural boundaries described in this document (the deterministic/probabilistic split, storage ownership, provider abstraction, the retrieval → `ReasoningContext` → reasoning flow). Work within them.
- Actively surface problems: ambiguities, internal inconsistencies, implementations that have drifted from the contracts, and specifications that are missing or underspecified. Naming these is valuable and expected.
- When a change exposes genuine architectural uncertainty — a contract is silent on a decision, or two sources appear to conflict — **stop before generating code.** Explain the ambiguity, lay out the reasonable implementation options with their trade-offs, and ask the user to choose. It is better to ask one good question than to guess and encode the guess.

The relationship is collaborative: Claude brings implementation judgment and a critical eye, the user owns architectural decisions.

## Architectural Authority

When sources of truth disagree, resolve the conflict by this precedence (highest first):

1. **Explicit instructions in the current conversation.**
2. **Runtime Domain Contracts** (`runtime_domain_contracts/`, `domain_contract_finalized.md`).
3. **Application Service Contracts** (`application_service_contracts/`, `application_service_finalized.md`).
4. **Architecture Decision Records / architectural documentation** (`philosophies.md`, `system_architecture_v2.md`, `docs/`, `current_plan.md`).
5. **README and repository documentation.**
6. **Existing implementation** (the code in `src/`).

Existing implementation is the **lowest** authority and is **not automatically correct.** Portions of the repository intentionally lag behind the finished architecture (see Development status). Do not treat code as the spec simply because it runs; when code and a higher-precedence source disagree, the higher source wins and the code is what needs to change — after confirming with the user if the change touches architecture.

## Architecture Freeze

The project is in the **implementation phase**, not the architecture-discovery phase. Treat the contracts as stable design documents. Claude should **not independently**:

- redesign, merge, or split services
- rename contracts or their concepts
- introduce new architectural patterns
- change ownership or responsibility boundaries
- alter orchestration responsibilities (what LangGraph vs. services vs. agents own)

This is not a ban on improvement ideas — those are welcome. If you see an architectural improvement, **present it as a separate suggestion** rather than silently implementing it. Whenever the architecture itself would change, pause and continue only after the user confirms the direction.

## Documentation Policy

Documentation here is expected to **run ahead of** implementation — architecture-first development means the docs describe the target and the code catches up. Consequences:

- Never silently rewrite documentation just because the code currently differs from it. A mismatch usually means the code hasn't caught up yet, not that the doc is wrong.
- When you find an inconsistency between documentation and implementation, **explain the discrepancy and ask which should become authoritative** before changing either.
- Amend architectural documentation only after explicit confirmation from the user.

The objective is to preserve architecture-first development: the design leads, the implementation follows.

## Engineering Workflow

This repository is developed architecture-first: contracts → domain models → application services → orchestration → infrastructure integration. Claude Code should operate like a senior/principal engineer working inside that flow — optimizing for architectural correctness, domain boundaries, and long-term maintainability, not just for producing code that passes.

### Implementation and Validation Workflow

Prefer deliberate implementation over an iterative trial-and-error coding loop.

When implementing a feature or change:

1. Inspect the relevant domain contracts, existing models, application services, repositories, orchestration boundaries, architectural documentation, and existing implementation patterns.
2. Reason about the intended design before modifying files.
3. Implement the complete requested scope rather than making small speculative changes followed by repeated validation cycles.
4. Review the implementation for consistency with architecture decisions, type safety, existing abstractions, naming conventions, and separation of responsibilities.
5. Provide the exact validation commands the user should run after implementation.

Avoid automatically entering this loop unless explicitly requested: modify code → write tests → run pytest → inspect failures → modify code → repeat. Do not use test execution as a replacement for architectural reasoning.

Avoid repeatedly running full pytest suites, type checkers, formatters, or other expensive validation commands after every small change. Prefer completing a coherent implementation unit first, then validating.

When tests are needed: add them at meaningful architectural boundaries, prioritizing contract, repository, service, and integration behavior. Avoid excessive tests for trivial implementation details. Explain what should be validated and provide commands rather than automatically executing them — the user prefers to review implementation progress and decide when validation commands should be executed.

### Token and Execution Efficiency

Optimize for high-quality reasoning rather than maximum tool execution. Before using tools or terminal commands, consider whether the information gained is valuable.

Avoid unnecessary repository exploration, redundant file reads, repeatedly inspecting unchanged files, rerunning commands that provide no new information, and generating large amounts of output without purpose.

Prefer focused repository inspection, fewer but more complete implementation steps, concise explanations, and grouped changes. Do not sacrifice correctness or engineering quality for token efficiency.

### AEGIS Architecture Discipline

Before implementing new functionality, determine whether the required abstraction already exists. Prefer extending established concepts rather than introducing new ones prematurely. Respect existing boundaries between domain models, application services, repositories, orchestration workflows, and infrastructure adapters.

If a requested implementation exposes a missing architectural boundary: explain the missing abstraction, discuss where it belongs in the architecture, and only then introduce the new concept. Do not bypass architectural layers for implementation convenience.

Avoid putting business logic inside infrastructure code, embedding orchestration logic inside domain models, creating duplicate concepts that overlap with existing contracts, or coupling application services directly to external providers when abstractions already exist.

### Testing Philosophy

Maintain the distinction between software correctness (unit tests, integration tests, contract tests, repository tests) and AI system evaluation (evaluation datasets, reasoning quality assessment, output quality measurement). Do not confuse traditional software tests with AI quality evaluation.

The project has a custom deterministic evaluation framework in `src/aegis/evaluation/` (CLI via `uv run aegis-eval`) that measures retrieval quality (Recall@K, MRR) and reasoning correctness offline, without the AI loop. Evaluation datasets and tests live separately in `evals/`. Tests are valuable, but they should be introduced intentionally at the correct boundary.

## Development status (important for interpreting the code)

**The runtime implementation is substantially complete.** The offline knowledge-compilation / indexing pipeline is production-oriented; the LangGraph orchestration layer is wired to real application services end to end; the CrewAI reasoning subsystem, HITL workflow, and deterministic evaluation framework are all implemented and integrated.

When reading or extending code, verify it against the finalized contracts in this order:
1. **Runtime Domain Contracts** and **Application Service Contracts** (the authoritative design).
2. Existing implementation (which should faithfully reflect the contracts).

If code and a contract diverge, the contract is authoritative — the code is what needs to change. Do not assume existing code is more correct simply because it runs; treat it as a candidate for verification and potential updating when you touch related areas.

Some boundary areas remain intentionally scaffolded as extension points (e.g., `src/aegis/retrieval/service.py` is a facade that delegates to the real `services/retrieval_service.py`). These are documented where they exist; do not treat them as incomplete implementations. Finalized design docs live in `runtime_domain_contracts/`, `application_service_contracts/`, `domain_contract_finalized.md`, `application_service_finalized.md`, and `current_plan.md`.

## Commands

Python is managed with **uv** (Python 3.12, `requires-python >=3.11,<3.13`). Prefix Python commands with `uv run`.

```bash
# Quality gate — run before considering work done (from Makefile `server-check`)
uv run ruff format
uv run ruff check
uv run mypy src            # mypy is strict = true

# Tests (pytest adds src/ to pythonpath via pyproject)
uv run pytest                                   # all
uv run pytest tests/indexing/test_pipeline.py   # one file
uv run pytest tests/indexing/test_pipeline.py::test_name   # one test
uv run pytest evals/                            # AI-quality evals (kept separate from tests/)

# Run the API (FastAPI on port 9000) -- AEGIS_PROFILE=production (default)
make dev-backend         # uv run uvicorn aegis.api.main:app --app-dir src --reload --port 9000

# Run the API against the demo profile (no GROQ_API_KEY / Redis creds needed)
make demo-server         # AEGIS_PROFILE=demo uv run uvicorn ... --port 9000

# Run the API against the demo-local profile (zero credentials: local vector index
# compiled from the seeded ICD taxonomy, no Upstash/Groq/OpenAI creds needed at all)
make demo-local          # AEGIS_PROFILE=demo-local uv run uvicorn ... --port 9000

# Frontend (React 19 + Vite, in frontend/, uses pnpm)
make dev-frontend        # cd frontend && pnpm run dev   (dev server on :5173)

# Database lifecycle
make db-init             # uv run aegis-db init --all --reset   (schema, drop+recreate)
make db-seed-icd         # seed icd11_taxonomy from ./data/only_medical_symptoms.csv

# Scripted end-to-end runs (submission -> AI reasoning -> HITL -> decision -> cache), through the real FastAPI app
make demo                # AEGIS_PROFILE=demo uv run python scripts/demo_e2e.py
make integration         # AEGIS_PROFILE=integration uv run python scripts/integration_e2e.py  (needs full .env)
make integration-cache   # same as integration, but submits the same note twice to prove cache MISS then HIT

# Evaluation harness (offline, no LangGraph)
uv run aegis-eval <retrieval|reasoning> --dataset ... --report ...
```

`uv run aegis-db` resolves normally via `pyproject.toml`'s `[project.scripts]` entry. The repo-root shim `./scaffold_db.py` (e.g. `./scaffold_db.py init --all --reset`, `./scaffold_db.py seed --icd`) remains available as a convenience for running the CLI without invoking `uv run`. CLI subcommands: `scaffold`, `init`, `seed`, `status`.

Note: `db-seed-icd` seeds from the curated `data/only_medical_symptoms.csv`, **not** the full WHO MMS export `data/icd11_mms_simplified.csv` — the curated file is what the offline embedding pipeline actually ran against (`state/upload_checkpoint.json` records `total=15471`, matching its row count). Seeding from the full export desyncs SQLite from the Upstash Vector index.

## Architecture

Three subsystems, mapped onto the deterministic/probabilistic boundary:

**Phase 1 — Offline knowledge compilation** (`src/aegis/indexing/`, `embeddings/`, `vectorstores/`, `jobs/`, `scripts/`). Runs only when the ICD-11 taxonomy changes. Deterministic, reproducible, no LangGraph. Reads the canonical ICD taxonomy from SQLite → `RepresentationBuilder` builds text representations (Title / Hierarchy / Prose variants) → `EmbeddingProvider` embeds → `VectorUploader` pushes to Upstash Vector. Upload is **resumable** via a checkpoint (`state/upload_checkpoint.json`). SQLite and Upstash Vector are independent outputs of the same compilation — neither depends on the other at runtime (pointer-based: the vector index returns ICD ids only; all descriptions/metadata stay in SQLite).

**Phase 2 — Deterministic runtime preparation** (`src/aegis/retrieval/`, plus early graph nodes). No LLMs. Anonymize → normalize → SHA-256 hash → Redis exact-match cache lookup → on miss, embed and query Upstash Vector → candidate ranking → assemble a single `ReasoningContext`. Retrieval retrieves *evidence only*; it does not diagnose. LangGraph/agents talk to retrieval through `retrieval/service.py`, never to Upstash directly.

**Phase 3 — Bounded AI reasoning** (`src/aegis/agents/`, `schemas/`, `prompts/`, `graphs/`). CrewAI reasoning agents perform bounded clinical reasoning over `ReasoningContext`; Pydantic schemas (`schemas/`) validate all model output before it enters the domain (PydanticAI is a declared dependency but not yet integrated — see the v2 roadmap in `docs/architecture.md`); human-in-the-loop physician review gates persistence; results are written transactionally to SQLite and the Redis cache is updated.

### Orchestration & persistence

- **LangGraph** (`graphs/workflow.py`, `graphs/nodes/`) is the macro state machine. `AegisWorkflowState` (`graphs/state.py`) is the shared state; statuses flow `PENDING_AI` → `PENDING_HITL` / `ARCHIVED`. Today the only conditional edge is deterministic cache-hit/miss routing (`_route_after_cache_lookup`): a cache hit ends the workflow, a miss routes unconditionally through `human_review_pending`. Confidence-based routing (auto-archiving high-confidence cases instead of always requiring human review) is a documented future capability — see `domain_contract_finalized.md`'s "Should AI auto-approve high confidence cases?" — not yet implemented; do not assume it exists. Graph checkpointing uses `AsyncSqliteSaver` against `data/graph_checkpoints.db`, set up in the FastAPI lifespan (`api/main.py`).
- **Two SQLite databases**: the clinical registry (system of record) and the LangGraph checkpoint/state DB. Schema is applied via **ordered numbered SQL migrations** in `src/aegis/database/migration/` (`0001_*` … `0012_*`), driven by lists in `database/database.py`. All connections enforce the same PRAGMAs (WAL, `busy_timeout=30000`, `synchronous=NORMAL`, `foreign_keys=ON`) — see `database/connection.py`. Concurrency uses **optimistic locking** via a `version` column (`graphs/optimistic_locking.py`); repository upserts raise `ValueError` on version collision.
- Repository persistence lives in `src/aegis/database/repositories/` (per-aggregate: `icd_repository.py`, `models.py`, plus stub files for future aggregates) and `src/aegis/infrastructure/sqlite/` (used by the graph nodes/services). The older monolithic `database/repository.py` + `database/adapters.py` (`ClinicalRegistryRepository`) described in earlier docs had no remaining callers and was removed.

### Provider abstraction

External AI and retrieval dependencies are isolated behind capability-specific abstractions rather than a generic provider layer:

- **Embedding providers** are behind `EmbeddingProvider` (`src/aegis/embeddings/`): `sentence_transformers.py` provides the default local implementation, while `openai.py` provides a swappable hosted alternative.
- **Vector stores** are behind `VectorStore` (`src/aegis/vectorstores/`, write path) and `VectorQueryProvider` (`src/aegis/retrieval/providers/`, read path): `upstash.py` in each provides the production retrieval backend, and `local.py` in each provides a credential-free implementation — used by the evaluation harness's fixture index and, at runtime, by the `demo-local` profile's compiled local index (`aegis.indexing.local_compiler`).
- **LLM reasoning access** is owned by the CrewAI infrastructure boundary (`src/aegis/infrastructure/crewai/reasoning_provider.py`). CrewAI manages model invocation through `crewai.LLM` and its LiteLLM integration; reasoning agents do not depend directly on model providers or infrastructure services.

The configured default LLM is Groq (`llama-3.3-70b-versatile`). The reasoning model is configured through the CrewAI LLM boundary rather than being coupled to the application architecture, allowing model changes without affecting workflow, service, or domain contracts. The configured default embedding provider is SentenceTransformers `BAAI/bge-large-en-v1.5` (1024 dimensions). OpenAI `text-embedding-3-small` (1536 dimensions) remains available as a swappable embedding implementation through `EMBEDDING_*` configuration.

### Runtime profiles (`AEGIS_PROFILE`)

`AppSettings.AEGIS_PROFILE` (`config.py`) is `"production" | "demo" | "demo-local" | "integration"`, read by the composition root (`api/bootstrap.py`) to decide which collaborators to wire up for four boundaries — cache, reasoning, content-repository, and (`demo-local` only) vector retrieval. Embedding stays real in every profile; Upstash Vector retrieval stays real in every profile except `demo-local`. See ADR-0002 (`docs/adr/0002-runtime-profile-architecture.md`) for the full rationale and ADR-0003 for `demo-local` specifically:

- **`production`** (default): real Redis-backed cache, real CrewAI/Groq reasoning, real Upstash Vector retrieval. Requires `GROQ_API_KEY` and the Upstash Redis pair (plus Upstash Vector + `EMBEDDING_*`, required in every profile below it).
- **`demo`**: the cache/reasoning/content-repository collaborators are replaced with deterministic in-memory fakes (`infrastructure/memory/`), so no `GROQ_API_KEY` or Redis credentials are needed — only Upstash Vector + embedding credentials. Built for the `docs/demo.md` walkthrough.
- **`demo-local`**: same in-memory fakes as `demo`, plus vector retrieval itself is replaced — `aegis.indexing.local_compiler` compiles the real seeded ICD-11 taxonomy into a local, file-backed vector index (cached under `.artifacts/local_vector_index/`) instead of querying Upstash Vector. Needs **no credentials at all**, not even a `.env` file — `EMBEDDING_PROVIDER`/`EMBEDDING_MODEL`/`EMBEDDING_DIMENSIONS` default to the same local model every other profile uses if left unset.
- **`integration`**: same real collaborators as `production`, under a separate profile name so `scripts/integration_e2e.py` can verify external infrastructure wiring without overloading the `production` profile semantics.

This is a config-driven dependency-injection switch, not a code fork — the graph, services, and API surface are identical across profiles; only what `bootstrap.py` injects changes. See `scripts/demo_e2e.py`, `scripts/integration_e2e.py`, `scripts/integration_cache_e2e.py`, and `scripts/e2e_common.py` for the scripted end-to-end runs that exercise each profile.

### Config

`src/aegis/config.py` — `AppSettings` (pydantic-settings) loads from `.env`, validates once at startup, and **fails fast** if any required secret is missing (`GROQ_API_KEY`, the four Upstash URL/token pairs — both conditional on `AEGIS_PROFILE`, see above). Access it via the cached `get_settings()`. See `.env.example` for the full variable set.

## Conventions

- **src layout**, package name `aegis` under `src/`. Imports are absolute from `aegis.*`. Tests and pytest rely on `pythonpath = ["src"]`; the API is run with `--app-dir src`.
- Ruff: line length **100**, rules `E, F, B, ASYNC, TCH`, LF line endings. `TCH` (flake8-type-checking) is active — keep type-only imports under `if TYPE_CHECKING:`; `pydantic.BaseModel` and `aegis.models.base.DomainModel` are configured as runtime-evaluated base classes.
- mypy runs in **strict** mode over `src` (frontend excluded). Use `from __future__ import annotations`.
- **Tests vs evals are deliberately separate.** `tests/` verifies deterministic software correctness (schemas, repositories, migrations, orchestration). `evals/` (with its own `conftest.py`) measures AI quality — Recall@K, MRR, nDCG, retrieval drift — and is expected to evolve independently. Don't fold eval metrics into unit tests.
