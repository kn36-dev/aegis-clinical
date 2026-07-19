# ADR-0003: Local Demo Execution Strategy

**Status:** Accepted

## Context

The existing `demo` profile (ADR-0002) already removes the need for `GROQ_API_KEY` and
Upstash Redis credentials, but it still requires `UPSTASH_VECTOR_REST_URL` /
`UPSTASH_VECTOR_REST_TOKEN` and the `EMBEDDING_*` settings, because it keeps retrieval real
against a live Upstash Vector index. That falls short of a genuinely zero-credential reviewer
path: `uv sync && make db-init && make db-seed-icd && make demo-local` should run the entire
clinical pipeline with no managed-service credentials of any kind, while still demonstrating
real semantic retrieval rather than a shortcut.

## Decision

Add `demo-local`, which reuses the `demo` profile's cache/reasoning/content substitutes and
additionally replaces retrieval itself. `aegis.indexing.local_compiler` runs the *same*
offline `IndexingPipeline` / `RepresentationBuilder` used to build the real Upstash-backed
index, but against the real, full ICD-11 taxonomy `make db-seed-icd` already seeds (not a
toy fixture), using the same default local embedding model
(`SentenceTransformers BAAI/bge-large-en-v1.5`) every other profile uses. The result is loaded
into the existing `LocalVectorStore` / `LocalVectorQueryProvider` abstraction (previously used
only by the evaluation harness's small fixture index) and persisted as a fingerprinted
artifact under `.artifacts/local_vector_index/` — a manifest records the taxonomy content
hash, row count, embedding model, and dimensions, so the (CPU-bound, multi-minute) compile
step runs at most once per taxonomy/embedding version rather than on every process start.

## Alternatives Considered

- **Fake retrieval** (return a small hardcoded set of ICD-11 candidates) — rejected.
  `ClinicalReasoningService` already rejects any recommended code absent from the real
  candidate set, so a hardcoded fixture would only work for whichever one note happens to
  match it. More fundamentally, it would misrepresent to a reviewer the one thing this profile
  exists to demonstrate honestly: that retrieval is genuine semantic search, not a scripted
  shortcut.
- **Rebuild the local vector index on every process start** — rejected. Embedding ~15,471
  taxonomy rows on CPU takes several minutes; paying that cost on every `make demo-local`
  invocation (and every `--reload` restart) is an unacceptable reviewer experience, and it
  contradicts the project's own Phase 1 doctrine that offline compilation runs only when the
  taxonomy changes — a doctrine that should hold for `demo-local`'s inline compile just as
  much as for the real Upstash-backed pipeline.
- **A smaller/faster local embedding model** (e.g. `all-MiniLM-L6-v2`) to make every start
  cheap without caching — rejected for now. It would diverge `demo-local`'s retrieval quality
  and embedding space from the model every other profile defaults to, making its retrieval
  behavior unrepresentative of the architecture it exists to showcase. The persisted-artifact
  approach solves the same "fast repeat startup" problem without that tradeoff.

## Consequences

- `demo-local`'s retrieval is genuine semantic search over the real taxonomy — the top
  candidate for a given note can differ from what `demo`'s live Upstash index returns (a
  different index, same embedding model), but it is never a fixture or a hardcoded shortcut.
- First run is still slow (validated at roughly 2–3 minutes for ~15,471 rows on typical
  hardware); every run after that loads the cached artifact in seconds, including across
  `--reload` restarts.
- The compiled artifact is a large (~350 MB, JSON) generated file that must stay gitignored —
  it is a build output, not application state, and is never committed.
- `LocalVectorQueryProvider`'s brute-force, pure-Python cosine-similarity scan is adequate for
  one reviewer's single-process local index but is explicitly not a production-scale retrieval
  path — this is documented (README, `docs/demo.md`) rather than silently presented as
  equivalent to Upstash Vector.
