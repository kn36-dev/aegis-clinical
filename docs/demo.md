# AEGIS Clinical — Demonstration Guide

> **Audience:** a senior engineer or hiring manager doing a live walkthrough or a
> self-guided review in ~10 minutes. This guide sequences the same commands documented in
> the root `README.md` — it adds narration, not new capability. Where this guide and the
> README disagree, the README wins (see `CLAUDE.md`'s Architectural Authority order).

---

## 1. Repository overview

`aegis-clinical` transforms unstructured clinical notes into structured ICD-11
classifications. It is a **reference architecture**, not a shipping product — the point is
to demonstrate a deterministic-orchestration-around-bounded-AI-reasoning pattern, not to be
a complete EHR coding tool.

Start orientation here, in order:

1. `README.md` — the 10-minute narrative, with the diagrams below embedded.
2. The **System Architecture** diagram (`system_architecture.mmd`) — layer map.
3. The **Clinical Processing Pipeline** diagram (`workflow_state_machine.mmd`) — the actual
   LangGraph state machine.
4. `docs/architecture.md` → `philosophies.md` → the runtime/application contracts, for
   anyone who wants the full depth.

The defining principle to keep in mind throughout: **deterministic systems own workflow
execution; probabilistic systems (LLMs) contribute bounded reasoning inside explicit
guardrails.** Every step below is a concrete instance of that split.

---

## 2. Backend startup

```bash
uv sync                              # once
make db-init && make db-seed-icd     # once — schema + ICD-11 taxonomy
AEGIS_PROFILE=demo make demo-server
# equivalent to: AEGIS_PROFILE=demo uv run uvicorn aegis.api.main:app --app-dir src --reload --port 9000
```

`AEGIS_PROFILE=demo` is the profile built for exactly this walkthrough (see
`aegis/api/bootstrap.py`): SQLite persistence, the full ICD-11 taxonomy, PHI
anonymization/normalization, the embedding provider, and Upstash Vector retrieval are all
**real** — the retrieval a reviewer sees is genuine similarity search over the real
~15,000-vector index. Only three collaborators are deterministic substitutes, each for a
reason documented in `docs/tradeoffs_and_limitations.md`: the cache (in-memory instead of
Redis), reasoning (a deterministic adapter that returns the top real retrieval candidate
instead of calling Groq/CrewAI), and the content repository (in-memory, pre-seeded sample
notes instead of freshly-typed text).

This means the demo needs only `UPSTASH_VECTOR_REST_URL` / `UPSTASH_VECTOR_REST_TOKEN` and
the `EMBEDDING_*` settings in `.env` — no `GROQ_API_KEY`, no Upstash Redis credentials.

Confirm it's up:

```bash
curl http://localhost:9000/health
# {"booted": true, "container_ready": true, "graph_ready": true}
```

> To demonstrate the **real** CrewAI/Groq reasoning path instead of the deterministic
> substitute, run `AEGIS_PROFILE=integration make integration` (needs `GROQ_API_KEY` +
> Upstash Redis credentials) — see the README's "Running the Demo Server" section for the
> full profile comparison.

### 2b. Zero-credential alternative: `demo-local`

`AEGIS_PROFILE=demo` above still requires `UPSTASH_VECTOR_REST_URL`/`UPSTASH_VECTOR_REST_TOKEN`
and the `EMBEDDING_*` settings — it keeps retrieval real against a live Upstash Vector index.
If you want to run the whole pipeline with **no credentials and no `.env` file at all**, use
`demo-local` instead:

```bash
uv sync                              # once
make db-init && make db-seed-icd     # once — schema + ICD-11 taxonomy
make demo-local
# equivalent to: AEGIS_PROFILE=demo-local uv run uvicorn aegis.api.main:app --app-dir src --reload --port 9000
```

`demo-local` reuses the same in-memory cache, reasoning, and content-repository substitutes as
`demo`, and additionally swaps retrieval itself: `aegis.indexing.local_compiler` compiles the
real ICD-11 taxonomy `make db-seed-icd` seeded (not a toy fixture) through the same offline
`IndexingPipeline` the real Upstash-backed index uses, embeds it locally with the same
SentenceTransformers model the other profiles default to, and serves queries from an in-memory
`LocalVectorQueryProvider`. Retrieval is still genuine semantic search over the real taxonomy —
never a hardcoded ICD code — just against a local index instead of Upstash Vector.

**First `demo-local` run compiles the local retrieval index; subsequent runs load it.** That
first compile embeds ~15,471 taxonomy rows on CPU, which takes several minutes; the result is
cached as a generated artifact under `.artifacts/local_vector_index/` (gitignored, never
committed) with a manifest fingerprinting the taxonomy content, embedding model, and dimensions,
so a changed taxonomy or embedding config triggers a recompile instead of silently serving a
stale index. Every subsequent `make demo-local` — including `--reload` restarts — loads that
cached artifact in seconds rather than recompiling.

Do not read `demo-local`'s retrieval quality or latency as representative of `demo` or
production: the brute-force local cosine-similarity query path exists for a credential-free
reviewer path, not as a production-scale retrieval backend. The architectural point it
demonstrates is narrower and, for this repo's purpose, more important — every external
infrastructure boundary (Upstash Vector, Upstash Redis, Groq) can be swapped at the composition
root (`aegis/api/bootstrap.py`) without changing the LangGraph workflow, application services, or
domain contracts at all.

---

## 3. Frontend startup

```bash
cd frontend
pnpm install                         # once
cp .env.example .env.local           # once — VITE_API_BASE_URL=http://localhost:9000
pnpm run dev
```

Open `http://localhost:5173`. The UI is a feature-based React 19 + Vite tree
(`frontend/src/features/`): `clinical-submission`, `review-queue`, `decision-detail`, and
`workflow-visibility` — there is no `Dashboard.tsx`/`ReviewConsole.tsx` (those names appear
only in archived mockups under `docs/history/frontend/`).

---

## 4. Submitting a clinical note

In the **demo** profile, the physician submission screen offers a fixed set of pre-seeded
sample notes (`aegis.api.bootstrap.DEMO_SAMPLE_NOTES`) rather than free text — this is a
deliberate limitation, not an oversight (see "Live-Credential Content Seeding Gap" in
`docs/tradeoffs_and_limitations.md`). Pick one and submit.

Behind that click, `POST /api/v1/clinical-notes` invokes the compiled LangGraph workflow
(`aegis.graphs.workflow.build_aegis_graph`):

```
create_clinical_note → normalize_note → cache_lookup
  → [cache hit]  → END (prior decision reused)
  → [cache miss] → retrieve_candidates → assemble_context → generate_recommendation
                 → human_review_pending (suspends here)
```

The **first** submission of a given sample note is always a cache miss — real embedding,
real Upstash Vector similarity search, then the deterministic top-candidate reasoning
adapter (or real CrewAI/Groq under `AEGIS_PROFILE=integration`) produces a
`CodingRecommendation`. **Resubmitting the same note** is the cache-hit path: it returns
instantly, with zero embedding or reasoning cost, reusing the previously physician-approved
`ClinicalDecision`. Submitting both back-to-back is the single clearest way to demonstrate
the one conditional edge that exists in this graph.

To watch the state machine execute stage by stage rather than just seeing the end result,
open the workflow-visibility view, or call the observability endpoint directly:

```bash
curl "http://localhost:9000/api/v1/workflows/{workflow_id}?include_artifacts=true"
```

(`include_artifacts=true` only returns data when the server also has
`EXPOSE_WORKFLOW_ARTIFACTS=true` set — it is a PHI/debug boundary that fails closed, not a
performance toggle.)

---

## 5. Human review workflow

A cache-miss submission suspends at `human_review_pending` — a real LangGraph
interrupt/resume boundary, not a UI-only pending state. The review queue
(`GET /api/v1/reviews/{thread_id}`) shows the recommended ICD-11 code(s) with their
retrieval evidence and reasoning; nothing downstream of this point has executed yet.

Submitting a decision (`POST /api/v1/reviews/{thread_id}/decision`) resumes the graph with
`Command(resume=...)`. The router never classifies dispositions itself — `decide_case`
(inside the graph) does, then:

```
decide_case → persist_clinical_decision → cache_store → END
```

Persistence to SQLite always happens **before** the Redis cache is updated — that ordering
guarantees only durably persisted clinical truth ever becomes reusable cached knowledge.
The decision-detail view reflects exactly what was written; refresh it to show the
now-cached note resolving instantly on resubmission (back to step 4).

---

## 6. Evaluation CLI

AI quality is evaluated separately from software correctness (`tests/`) — this is the
`aegis-eval` CLI (`src/aegis/evaluation/`), reusing the same real `RetrievalService` /
`ContextAssembler` the production workflow uses, not a mocked harness:

```bash
uv run aegis-eval retrieval --config config/evaluation.yaml   # Recall@K, Hit Rate@K, MRR
uv run aegis-eval reasoning --config config/evaluation.yaml   # schema validity, code alignment, grounding
uv run aegis-eval all       --config config/evaluation.yaml   # both
```

Each run writes a reproducible, provenance-stamped report (git commit, dataset hash, config
hash, model/provider) under `.artifacts/evaluations/`. There is no LLM-as-judge scoring and
no Braintrust integration yet — both are labeled **Future v2** in `docs/architecture.md`
and `docs/testing_and_evaluations.md`; don't present them as running today.

---

## 7. Repository structure

```text
aegis-clinical/
├── src/aegis/
│   ├── api/            FastAPI app, routers, bootstrap composition root
│   ├── graphs/          LangGraph workflow, nodes, state, checkpointing
│   ├── services/         Deterministic application services
│   ├── agents/ schemas/ prompts/   Bounded CrewAI reasoning + validation
│   ├── indexing/ embeddings/ vectorstores/   Offline knowledge compilation
│   ├── retrieval/       Runtime retrieval preparation
│   ├── database/         Migrations, connection, repositories, CLI
│   ├── infrastructure/    SQLite / Redis / Upstash / CrewAI adapters
│   └── evaluation/       aegis-eval — AI-quality evaluation framework
├── frontend/src/features/   clinical-submission · review-queue · decision-detail · workflow-visibility
├── runtime_domain_contracts/, application_service_contracts/   Authoritative design
├── docs/                 Reader-facing docs (+ docs/history/ for superseded material)
├── evals/                AI-quality eval dataset (clinical_cases.jsonl)
└── tests/                 Deterministic software-correctness tests
```

See the README's "Repository Structure" section for the full annotated tree.

---

## 8. Architecture overview

For the diagrams and the deeper narrative, see:

- **`README.md`** — "System Architecture", "Retrieval: Offline Compilation vs. Runtime
  Inference", and "Clinical Processing Pipeline" (all three Mermaid diagrams live here).
- **`docs/architecture.md`** — the three subsystems, storage ownership table, and the
  Future v2 roadmap (PydanticAI, Braintrust, OpenTelemetry — none implemented today).
- **`docs/orchestration.md`** — exactly what LangGraph owns and does not own.
- **`docs/crewAI_architectural_decision.md`** — why a single reasoning agent, not a crew.
- **`docs/tradeoffs_and_limitations.md`** — the demo-specific limitations referenced
  throughout this guide.

One closing point worth making explicit in a walkthrough: every diagram and claim in this
guide was checked against the code that runs today, not against the target design. Where
the two differ, the gap is called out — not papered over.
