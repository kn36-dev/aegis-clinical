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

---

## Deferred AI-Assisted Trial Eligibility Parsing

Future iterations may introduce AI-assisted parsing of free-text eligibility criteria into structured trial requirements. This capability was intentionally deferred because it would require an additional reasoning pipeline, increasing inference cost, orchestration complexity, and evaluation surface beyond the primary objective of demonstrating deterministic clinical note processing.

---

## Indexing / Representation Strategy (Deferred)

The current system intentionally adopts a single structured-prose representation for ICD-11 concepts to maintain a clean, interpretable baseline for evaluation and to avoid premature complexity in the indexing layer. Future iterations may extend this design to support multiple semantic representations of the same ICD concept, including title-based identity-focused encoding, hierarchical ontology-structured encoding, structured clinical prose encoding, and parent-context expanded ontology views. Each representation would produce an independent embedding for the same ICD concept, resulting in multiple vector entries per concept within the Upstash Vector index. This approach enables a deliberate trade-off between storage and indexing overhead versus retrieval robustness, increasing semantic coverage and reducing sensitivity to query phrasing variance. However, it also introduces duplication costs and additional indexing complexity, so it is intentionally deferred until the single-representation baseline has been empirically validated.
---

## Embedding Strategy (Deferred)

The current implementation standardizes all ICD-11 embedding generation on OpenAI’s text-embedding-3-small model to maintain consistency and ensure a stable baseline for retrieval evaluation. Future improvements may explore domain-specialized embedding models, such as biomedical or clinical transformer models from Hugging Face, to improve semantic alignment between patient-generated clinical notes and structured ICD-11 representations. These alternatives would be evaluated in a controlled experimental setup using retrieval benchmarks such as Recall@K, MRR, and nDCG against the existing baseline model to ensure that any increase in model or system complexity produces measurable improvements in retrieval performance. This exploration is intentionally deferred to avoid premature model specialization and to preserve a clear, reproducible baseline before introducing additional variables into the embedding pipeline.

---

## Clinical Note Normalization Strategy (Incremental)

The current retrieval architecture intentionally assumes that modern embedding models can bridge much of the semantic gap between free-form clinical notes and structured ICD-11 concepts, enabling a retrieval-first pipeline without requiring an upfront LLM-based symptom extraction stage. However, this assumption has practical limitations, as real-world clinical documentation frequently contains negation, temporal relationships, historical findings, demographic references, abbreviations, and varying levels of specificity that cannot always be represented faithfully within a single embedding space. To reduce this semantic ambiguity while preserving deterministic execution, the system introduces an incremental clinical note normalization layer prior to embedding generation. This layer prioritizes rule-based extraction and normalization of high-value clinical signals—such as patient age, negated findings, temporal expressions, and relevant medical history—using deterministic techniques wherever practical before considering probabilistic methods. The initial implementation intentionally focuses on the highest-impact and most reliably extractable signals (beginning with age and negation detection), with additional normalization capabilities introduced incrementally as the system matures. This design acknowledges that no preprocessing pipeline can perfectly eliminate clinical ambiguity, but deliberately favors explainable, reproducible, and deterministic improvements over premature dependence on LLM-based interpretation, reserving probabilistic reasoning for downstream tasks where contextual clinical judgment provides demonstrable value.

---

## Semantic Dependency Tradeoff: Embedding Model as System-Level Meaning Layer

The architecture intentionally consolidates semantic interpretation into the embedding model, which serves as the primary interface between free-form clinical notes and structured ICD-11 concepts, replacing earlier multi-stage approaches such as LLM-based symptom extraction with a unified retrieval space. This reduces orchestration complexity and improves system determinism, but introduces a core dependency on the embedding model’s representational quality, as it now implicitly handles semantic feature extraction, medical language normalization, and mapping to ICD ontology space. As a result, system correctness is increasingly determined by embedding space geometry rather than procedural logic, making model selection a system-level decision evaluated through retrieval benchmarks (Recall@K, MRR, nDCG) against a fixed ICD-11 ground truth. This tradeoff is accepted in exchange for simpler pipelines, lower inference cost, and clearer separation between indexing and retrieval stages, while more complex approaches such as multi-representation indexing or hybrid retrieval are explicitly deferred to maintain a stable and reproducible baseline.

---

## Free Tier Operational Constraint

The current implementation targets the Upstash Vector free tier during development. This environment enforces a daily update quota that is significantly lower than the complete ICD taxonomy. Rather than embedding provider-specific quota handling into the indexing architecture, operational concerns such as checkpointing, resumable uploads, and scheduled batch execution are intentionally separated from the core indexing pipeline. This preserves a clean architectural boundary between deterministic indexing logic and deployment-specific operational workflows. In production deployments, where vector databases typically support substantially higher ingestion throughput, these operational utilities can be replaced or omitted without affecting the indexing pipeline or domain architecture.

---

## External Vector Store Dependency Tradeoff

The system intentionally integrates with Upstash Vector for production-like semantic indexing capabilities. However, Upstash operates under external quota and provisioning constraints that are outside the control of this system. To preserve architectural correctness, the vector store is abstracted behind a provider interface, allowing interchangeable deployment modes:
- Local mode: in-memory or local vector store for reproducible execution
- Cloud mode: Upstash Vector for realistic production deployment
This design ensures reproducibility of the core indexing pipeline while acknowledging external infrastructure limitations. Full end-to-end cloud reproduction requires external credentials and is not part of the deterministic system boundary.

---

## Live-Credential Content Seeding Gap

A fresh clinical note submission run against the real, fully credential-backed runtime cannot complete today. `ClinicalNote.case_id` is generated only once a submission reaches `ClinicalNoteService`, so no caller can know it in advance; the SQLite-backed content store's `clinical_note_content` table, however, requires a `patient_case` row to already exist for that case_id before content can be associated with it, and there is no seam in the workflow between note creation and normalization for a caller to seed that content mid-flight. The practical consequence is that a fresh submission against the real, credentialed adapters fails during normalization when it attempts to resolve `content_reference` into note text, and the ingestion endpoint reports this as a 502.

This is documented rather than patched, because the available fixes are both architectural changes outside this slice's scope: relaxing the content store's referential integrity to the patient case, or making `case_id` supplied by the caller rather than generated by `ClinicalNoteService`. The credential-free demonstration path (`scripts/demo_e2e.py`, `tests/integration/test_clinical_pipeline.py`) sidesteps this by substituting a fake content repository that resolves any reference from an in-memory mapping with no case-identity dependency, which is sufficient to exercise the full workflow, interrupt/resume, and persistence-then-cache ordering end to end — just not the live content-seeding path itself, which remains a known gap for a future slice to close.