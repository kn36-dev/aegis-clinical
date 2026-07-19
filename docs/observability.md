# AEGIS Clinical — Observability

> **v1 implementation.** This describes observability as it exists today. OpenTelemetry is
> **not** wired up — it is a Future v2 enhancement (see the roadmap below).

## v1: workflow-state visibility

AEGIS's current observability is workflow-centric rather than telemetry-centric — the
priority is making the deterministic execution path inspectable:

- **Workflow inspection endpoint.** `GET /api/v1/workflows/{workflow_id}` exposes a
  workflow's current node and status by reading LangGraph checkpoint state.
- **Review queue + stage timeline (frontend).** The React dashboard
  (`frontend/src/features/workflow-visibility/WorkflowStageTimeline.tsx`,
  `review-queue/`, `decision-detail/`) visualizes where each case sits in the pipeline and
  surfaces pending physician reviews.
- **Checkpoint durability.** `AsyncSqliteSaver` against `data/graph_checkpoints.db`
  persists workflow state, so a suspended/interrupted case can be inspected and resumed
  deterministically.
- **Structured application logging** at API and node boundaries.

This is sufficient to answer "where is this case, and why is it waiting?" without a
tracing stack.

## Future v2: OpenTelemetry

Not implemented today. A production observability enhancement would add:

- distributed tracing across API → LangGraph nodes → services → infrastructure,
- span-level timing (retrieval latency, reasoning latency, node execution time),
- token-usage and cost metrics, and similarity statistics,
- checkpoint/trace correlation (checkpoints carrying trace ids rather than full spans),
- OTLP export to a dedicated backend (Jaeger, Grafana Tempo, OpenObserve, or another
  OpenTelemetry-compatible platform).

Instrumentation would attach at FastAPI and LangGraph node boundaries. This is roadmap;
no OpenTelemetry dependency or instrumentation exists in the codebase today. Some
metrics in `docs/testing_and_evaluations.md` (e.g. the cache-efficiency cost curve) depend
on this future instrumentation and are labeled accordingly.
