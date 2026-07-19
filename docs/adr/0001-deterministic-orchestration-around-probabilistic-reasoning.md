# ADR-0001: Deterministic Orchestration Around Probabilistic Reasoning

**Status:** Accepted

## Context

`aegis-clinical` uses an LLM to interpret free-text clinical language against semantically
retrieved ICD-11 candidates — a task only a language model can do well. But the surrounding
system controls whether a clinical note is cached, retrieved against, sent for AI reasoning,
routed to a physician for review, and persisted as an authoritative clinical decision. If the
LLM (or an agent wrapping it) can influence *those* decisions — which state to transition to,
whether to skip human review, what to write to the system of record — then the system's
correctness becomes only as predictable, testable, and auditable as the model itself. That is
an unacceptable property for a clinical-coding workflow, and it is also a poor fit for a
portfolio meant to demonstrate rigorous AI systems engineering rather than an agent demo.

## Decision

Split the system into deterministic orchestration and bounded reasoning, with an explicit,
enforced boundary between them:

- **LangGraph** (`graphs/workflow.py`) owns the workflow topology. `AegisWorkflowState` state
  transitions are fixed; the only conditional edge in the graph
  (`_route_after_cache_lookup`) is deterministic code branching on a `CacheService` lookup
  result, never on anything the model produced. Human-in-the-loop review is a real
  interrupt/resume suspension (`human_review_pending`), not a UI-only pending flag.
- **Application services** (`src/aegis/services/`) own every decision the graph delegates:
  what counts as a cache hit, how candidates are ranked, in what order persistence and cache
  projection happen (SQLite write before Redis update, always).
- **CrewAI** (`src/aegis/agents/`, `infrastructure/crewai/`) is handed a deterministic
  `ReasoningContext` — normalized note text plus the bounded candidate set retrieval already
  found — and returns a structured `CodingRecommendation`. It cannot call any infrastructure
  directly (no SQLite, Redis, Upstash Vector, or embedding-provider access from inside the
  agent), and `ClinicalReasoningService` rejects any recommended code that is not among the
  candidates it was actually given — the model can rank and justify, but it cannot invent an
  ICD-11 code or select one retrieval never surfaced.

This is the project's defining principle, stated once and enforced everywhere above:
**the application governs the AI; the AI never owns the application.**

## Alternatives Considered

- **Autonomous agent orchestration** (a CrewAI crew that plans its own steps and calls tools,
  including retrieval or persistence, directly) — rejected. This makes the workflow's actual
  call graph only as reproducible as the model's planning behavior on a given run, breaks
  deterministic testing (`tests/` cannot enumerate what an autonomous agent might decide to
  do), and removes the clean, auditable point at which a physician reviews AI output before
  it becomes clinical truth.
- **Direct LLM function-calling against infrastructure** (letting the model call the vector
  store or write to SQLite itself) — rejected. It collapses the provider-abstraction boundary
  documented in `runtime_domain_contracts/`, and it means a prompt-injected or malformed model
  response could directly mutate persisted clinical state rather than being caught by
  `ClinicalReasoningService`'s validation first.
- **Confidence-based auto-routing** (skip human review above a confidence threshold) — not
  rejected, deferred. `domain_contract_finalized.md` documents this as a real future
  capability. Even in that design, the *decision to skip review* stays deterministic code
  comparing a validated confidence score against a coded threshold — the model still never
  decides its own review requirement.

## Consequences

- Every workflow path is enumerable and testable without a real LLM call: `tests/` exercises
  the graph with fake reasoning providers, and `demo`/`demo-local` swap in
  `DeterministicTopCandidateReasoningProvider` without touching orchestration at all.
- The reasoning boundary (Groq/CrewAI vs. a deterministic adapter) is swappable purely at the
  composition root (`api/bootstrap.py`) — see ADR-0002 — because nothing about workflow
  correctness depends on which one is wired in.
- Human review is a real suspension point that can be inspected
  (`GET /api/v1/workflows/{workflow_id}`), not a cosmetic frontend state.
- The tradeoff: the model cannot influence workflow shape even when it might have a useful
  signal to offer (e.g., "this case looks urgent"). Any such capability has to be added as an
  explicit, reviewed contract change — a new deterministic routing rule that *consumes* a
  validated model output — never as emergent behavior from giving the model more control.
