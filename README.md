# aegis-clinical 🛡️

## Deterministic AI Orchestration for Clinical Note Structuring

`aegis-clinical` is a reference architecture demonstrating how modern AI systems can safely transform unstructured clinical notes into structured ICD-11 classifications through deterministic workflow orchestration, semantic retrieval, and human-in-the-loop validation.

Rather than relying on autonomous agent loops, the system combines explicit state-machine orchestration with bounded AI reasoning to ensure every clinical note follows a deterministic execution path from ingestion through physician approval. The repository emphasizes architectural correctness, clear data ownership, reproducible execution, and evaluation-driven development over infrastructure scale.

---

# Architectural Overview

The application is intentionally organized around clear responsibility boundaries, where every major component owns exactly one concern.

### LangGraph — Deterministic Workflow Orchestration

LangGraph acts as the macro-orchestrator of the application. It defines the immutable execution topology responsible for sequencing data anonymization, semantic retrieval, AI-assisted reasoning, physician review, persistence, and workflow resumption. Human-in-the-Loop (HITL) checkpoints suspend execution safely until physician approval before allowing downstream state transitions.

### CrewAI — Parallel Domain Reasoning

CrewAI encapsulates specialized worker agents responsible for bounded reasoning tasks, including symptom extraction, ICD-11 candidate analysis, and medical validation. Agent execution remains isolated inside deterministic workflow boundaries rather than controlling application flow directly.

### PydanticAI — Structured Validation Boundary

All AI-generated outputs pass through strongly typed PydanticAI models before entering the application domain. This boundary converts probabilistic language model responses into deterministic application objects while rejecting malformed, incomplete, or semantically invalid outputs before they reach persistence layers.

---

# Storage Architecture

The persistence layer follows a strict separation of responsibilities.

### SQLite — System of Record

SQLite serves as the authoritative source of truth for all mutable application state, including clinical cases, physician-approved ICD-11 classifications, audit history, workflow checkpoints, optimistic versioning, and the complete ICD-11 taxonomy. Write-Ahead Logging (WAL) mode enables concurrent reads while preserving transactional consistency.

### Upstash Vector — Semantic Retrieval

A single Upstash Vector index contains a read-only `taxonomy_lookup` namespace populated with precomputed embeddings of the official ICD-11 taxonomy using OpenAI's `text-embedding-3-small` embedding model.

The vector database functions exclusively as a semantic nearest-neighbor index, returning ICD-11 identifiers during similarity search. Clinical descriptions, taxonomy metadata, and application state remain solely within SQLite, following a pointer-based architecture that avoids duplicated mutable data across storage systems.

### Upstash Redis — Deterministic Cache

Redis provides an exact-match cache keyed by the SHA-256 hash of normalized clinical notes. Previously processed notes bypass semantic retrieval and AI reasoning entirely, returning physician-approved ICD-11 classifications with zero additional embedding generation or LLM inference cost. This deterministic cache improves efficiency over time while preserving SQLite as the authoritative data source.

---

# Clinical Processing Pipeline

Every clinical note progresses through a deterministic execution pipeline:

1. PHI anonymization and normalization.
2. Deterministic Redis cache lookup using the normalized note hash.
3. Semantic retrieval of candidate ICD-11 codes from Upstash Vector upon cache miss.
4. Parallel AI-assisted validation through CrewAI workers.
5. Structured validation via PydanticAI.
6. Human-in-the-Loop physician approval.
7. Transactional persistence into SQLite.
8. Deterministic Redis cache update for future identical requests.

This architecture intentionally combines deterministic state transitions with bounded AI reasoning, ensuring that probabilistic model outputs never directly control workflow execution.

---

# Repository Structure

```text
aegis_clinical/
├── .github/
│   └── workflows/              # Continuous Integration
├── data/                       # Synthetic datasets and ICD-11 resources
├── docs/                       # Detailed architecture documentation
├── evals/                      # Evaluation harnesses and benchmark datasets
│   ├── datasets/
│   ├── metrics/
│   └── scenarios/
├── src/
│   └── aegis/
│       ├── agents/             # CrewAI worker implementations
│       ├── graphs/             # LangGraph workflow definitions
│       ├── schemas/            # PydanticAI models
│       ├── storage/            # SQLite, Redis and Vector adapters
│       ├── services/           # Domain services
│       ├── hitl/               # Human-in-the-Loop workflow management
│       └── observability/      # OpenTelemetry instrumentation
├── tests/
│   ├── unit/                   # Isolated component verification
│   ├── integration/            # End-to-end application behaviour
│   └── fixtures/
├── pyproject.toml
└── README.md
```

---

# Verification Strategy

The repository distinguishes functional correctness from AI quality evaluation.

## Unit Tests

Verify deterministic business logic, schema validation, state transitions, and utility functions independent of external AI providers.

## Integration Tests

Validate complete workflow execution across orchestration, persistence, checkpointing, and Human-in-the-Loop interactions using synthetic datasets.

## Evaluation Harness

Evaluation suites are maintained independently from traditional software tests. Rather than verifying functional correctness, they measure AI system behaviour, including ICD-11 extraction quality, semantic retrieval effectiveness, workflow invariants, regression detection, and structured output stability. This separation allows deterministic software verification and probabilistic AI evaluation to evolve independently.

---

# Engineering Principles

The architecture is guided by several core design principles:

* Deterministic workflow execution over autonomous agent control.
* Single source of truth for all mutable application state.
* Explicit separation between orchestration, reasoning, validation, and persistence.
* Pointer-based semantic retrieval without duplicated mutable metadata.
* Evaluation-driven AI development with reproducible benchmarks.
* Minimal infrastructure complexity while preserving clear production evolution paths.
