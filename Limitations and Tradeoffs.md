## Why SQLite Instead of PostgreSQL?

SQLite is intentionally selected to minimize operational overhead while keeping the project's focus on deterministic AI orchestration rather than infrastructure engineering. Although PostgreSQL would provide superior concurrency, replication, partitioning, and operational scalability, those capabilities are orthogonal to the architectural concepts this repository aims to demonstrate. SQLite also enables the project to be cloned and executed with virtually zero setup, improving reproducibility for reviewers. The repository nevertheless includes production-oriented schema definitions to demonstrate that the relational model is portable to a larger database engine if required.

---

## Why Isn't the `patient_identity_vault` Fully Secured?

The portfolio intentionally demonstrates where sensitive data boundaries exist without implementing the complete security infrastructure expected in a production clinical environment. A real deployment would incorporate encrypted storage, application-layer encryption, cloud-backed key management, private network isolation, role-based access control, and comprehensive auditing. These concerns are deliberately scoped out because they showcase infrastructure and security engineering rather than the AI orchestration, workflow design, and human-in-the-loop architecture that this project emphasizes.

---

## Separation of Checkpoint State and Observability

Workflow checkpoints intentionally store only the minimum state required for deterministic execution resumption, including trace correlation identifiers rather than complete OpenTelemetry spans. Runtime telemetry is emitted independently through OpenTelemetry, allowing workflow persistence and observability to evolve as separate concerns. In production, these traces would typically be exported via OTLP to a dedicated backend such as Jaeger, Grafana Tempo, or OpenObserve; the portfolio implementation keeps the observability stack intentionally lightweight to maximize reproducibility while still demonstrating end-to-end instrumentation patterns.

---

## Production Operational Concerns

The following capabilities are intentionally omitted because they primarily demonstrate production operations rather than AI systems engineering:

* Backup and recovery strategies
* Database migration workflows
* Encryption at rest
* PHI key management
* Role-based access control (RBAC)
* Data retention policies
* Immutable audit storage
* Disaster recovery planning

---

## Deferred Architectural Evolution: Semantic Institutional Memory

The application intentionally limits semantic retrieval to the static ICD-11 taxonomy and deterministic Redis caching for exact repeat detection. A second vector namespace containing embeddings of physician-approved clinical notes would become valuable only after accumulating a sufficiently large corpus of validated cases, enabling semantic retrieval over historical clinical decisions. That additional retrieval layer is deliberately deferred because it introduces another embedding lifecycle, synchronization path, and vector index without providing proportional value for a portfolio-scale workload. The current architecture therefore favors minimal operational complexity while leaving a clear evolution path toward institutional semantic memory for larger production deployments.

---

## Deferred Distributed Coordination

The repository intentionally targets a reference deployment consisting of a single application instance to keep the focus on AI orchestration and deterministic workflow execution. Distributed coordination mechanisms—such as Redis-based locks, provider-aware rate limiting, and multi-replica workflow ownership—are natural production evolutions once the application is horizontally scaled.

---

## Single Source of Truth

The project intentionally avoids duplicating mutable clinical note content inside Upstash Vector metadata. Vector records serve exclusively as semantic indexes returning stable identifiers, while SQLite remains the sole authoritative source of clinical text and relational state. This pointer-based architecture minimizes synchronization complexity, eliminates metadata drift, and keeps the semantic index focused solely on approximate nearest-neighbor retrieval.