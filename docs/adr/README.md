# Architecture Decision Records

This directory holds lightweight ADRs for decisions where the *reasoning* — not just the
resulting code — is worth preserving for a reader evaluating the architecture. It is a new
addition, introduced because the repository had no dedicated ADR location: related
single-decision write-ups already existed (`docs/crewAI_architectural_decision.md`,
`docs/tradeoffs_and_limitations.md`), but nothing indexed them as a set or gave them a
consistent shape. This directory formalizes that pattern; it does not replace those files,
which stay as focused, narrative deep-dives an ADR here can link to.

**Format.** Each ADR is one Markdown file, numbered sequentially (`NNNN-kebab-title.md`),
with four sections:

- **Context** — the constraint or problem that forced a decision.
- **Decision** — what was actually decided, in concrete terms (names of real
  files/classes/config, not abstractions).
- **Alternatives Considered** — the other options weighed, and why each was rejected or
  deferred rather than chosen.
- **Consequences** — what the decision costs as well as what it buys; a decision with only
  upsides usually means the tradeoff was not stated honestly.

**When to add one.** Only for decisions a principal engineer reviewing this repository would
otherwise have to reverse-engineer from a diff — a real fork in the road where a different
choice was plausible. Do not write an ADR for an implementation detail that follows
mechanically from an already-decided contract; that belongs in code comments or the relevant
`runtime_domain_contracts/` / `application_service_contracts/` document instead.

**Status.** All ADRs below are `Accepted` and already reflected in the current
implementation — this repository is past the architecture-discovery phase (see CLAUDE.md's
"Architecture Freeze"), so nothing here is `Proposed`.

## Index

- [ADR-0001 — Deterministic Orchestration Around Probabilistic Reasoning](0001-deterministic-orchestration-around-probabilistic-reasoning.md) —
  why LangGraph and the application services own every control-flow decision, and CrewAI/LLMs
  never do.
- [ADR-0002 — Runtime Profile Architecture](0002-runtime-profile-architecture.md) — why
  `AEGIS_PROFILE` is a composition-root dependency-injection switch, not a code fork or a
  separate demo application.
- [ADR-0003 — Local Demo Execution Strategy](0003-local-demo-execution-strategy.md) — why
  `demo-local` compiles a real, persisted local vector index instead of faking retrieval,
  rebuilding it on every start, or swapping to a smaller embedding model.
