# ADR-0002: Runtime Profile Architecture

**Status:** Accepted

## Context

The project needs to run credibly in several different execution environments: a reviewer
with no managed-infrastructure credentials at all, a live demo with genuine retrieval but no
per-request LLM cost, an environment that verifies every external credential and adapter
actually works end to end, and a real production deployment. These environments differ only
in *which infrastructure is real*, never in what the application is supposed to do — so
whatever mechanism selects between them must not let "which environment" become a second,
implicit description of the system's behavior that can drift from what actually ships.

## Decision

Introduce `AEGIS_PROFILE` (`production` | `demo` | `demo-local` | `integration`) as a single
configuration value, read once by the composition root (`api/bootstrap.py`), that selects
which concrete infrastructure adapter is constructed for a small, fixed set of boundaries:

- cache (`build_cache_repository`)
- reasoning (`build_reasoning_provider`)
- content repository (`build_content_repository`)
- vector retrieval (`build_vector_query_provider` — only branches for `demo-local`)

Every other collaborator — the FastAPI app, routers, the compiled LangGraph graph, and every
application service — is constructed identically regardless of profile. No router, service,
or graph node contains an `if AEGIS_PROFILE == ...` check; the branching exists in exactly
`api/bootstrap.py` (plus one profile-gated read in the demo-patients router, since that
dataset is genuinely profile-scoped, not the behavior around it).

## Alternatives Considered

- **A separate demo application or codebase** — rejected. It would guarantee drift between
  what a reviewer sees and what production actually runs, double the maintenance surface, and
  defeat the stated purpose of a reference architecture: the demoed behavior has to *be* the
  production behavior, not an approximation of it.
- **Conditional branches scattered through services and graph nodes** — rejected. This would
  leak a deployment concern into business logic, and would make it false to claim (as
  `docs/architecture.md` does) that "the graph layer has no infrastructure imports of its
  own." It would also make adding a profile a shotgun-surgery change touching many files
  instead of one.
- **Independent per-capability feature flags instead of one named profile** — considered, and
  partially present in spirit: each boundary (cache/reasoning/content/retrieval) is already
  independently swappable inside `bootstrap.py`. A single named profile is kept as the
  externally-facing selector anyway, so a reviewer reasons about one dial ("how real is this
  run") instead of four independent ones that could, in principle, be combined into
  combinations nobody has actually validated.

## Consequences

- Adding the fourth profile (`demo-local`, see ADR-0003) required changes only in
  `bootstrap.py`, `config.py`, and documentation — zero changes to `graphs/`, `services/`, or
  the domain contracts, and one narrowly-scoped router change (the demo-patients endpoint).
- Every profile is exercised by the same scripted end-to-end harness
  (`scripts/e2e_common.py`, `scripts/demo_e2e.py`, `scripts/integration_e2e.py`) — the
  workflow logic under test is never duplicated per profile.
- `AppSettings.__init__` (`config.py`) enforces the credential requirements per profile at
  startup (fail-fast), so a misconfigured profile cannot silently start with a missing
  credential and fail later, mid-request.
- The tradeoff: `bootstrap.py` accumulates one branch per boundary per new profile. At four
  profiles this is still a handful of `if settings.AEGIS_PROFILE in (...)` conditionals in one
  file — legible at a glance. If profiles keep multiplying, this will eventually want a more
  structured registry (a mapping of profile → adapter factory) rather than inline
  conditionals; not needed yet, and deliberately not built ahead of that need.
