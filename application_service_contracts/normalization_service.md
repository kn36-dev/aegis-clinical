# Application Service Contract — NormalizationService

## Purpose

`NormalizationService` is responsible for producing an immutable `NormalizedClinicalNote` from an immutable `ClinicalNote`.

It represents the deterministic preprocessing boundary of the AEGIS runtime pipeline, transforming the original clinical observation into a standardized, privacy-preserving representation suitable for semantic retrieval and downstream AI-assisted reasoning.

The service performs no clinical interpretation, diagnosis, coding, or probabilistic reasoning. Its sole responsibility is deterministic normalization.

---

# Ownership

## Creates

`NormalizedClinicalNote`

The service exclusively owns construction of the normalized runtime artifact.

No other component—including LangGraph, FastAPI, CrewAI, or infrastructure adapters—should instantiate `NormalizedClinicalNote` directly.

The creation boundary is:

```
ClinicalNote

        ↓

NormalizationService

        ↓

NormalizedClinicalNote
```

This ensures that every normalized artifact is produced using the same deterministic normalization specification.

---

## Consumed By

After creation, `NormalizedClinicalNote` may be consumed by:

- CacheService
- RetrievalService
- Workflow orchestration
- Audit systems

Downstream components must never modify or recreate the normalized artifact.

---

# Lifetime

`NormalizedClinicalNote` is immutable.

It represents the exact deterministic output produced from a specific `ClinicalNote` using a specific normalization specification.

If normalization rules evolve, a new immutable artifact must be generated.

Example:

```
ClinicalNote

        ↓

Normalization Specification v1.0

        ↓

NormalizedClinicalNote v1.0

──────────────────────────────

Normalization Specification v2.0

        ↓

NormalizedClinicalNote v2.0
```

Historical normalized artifacts remain valid for auditability and reproducibility.

---

# Primary Responsibilities

## 1. Content Retrieval

The service retrieves the original clinical narrative using the `content_reference` contained within `ClinicalNote`.

The retrieval mechanism is abstracted behind a repository interface.

The service does not depend on storage technology.

---

## 2. Deterministic PHI Anonymization

The service removes or anonymizes protected health information using deterministic rules.

Given identical input and normalization specification, the anonymized output must always be identical.

The service performs no probabilistic anonymization.

---

## 3. Text Normalization

The service applies deterministic normalization operations, including where appropriate:

- whitespace normalization
- formatting normalization
- terminology standardization
- Unicode normalization
- punctuation normalization

The exact normalization specification remains implementation-defined but must be deterministic.

---

## 4. Runtime Artifact Construction

The service constructs an immutable `NormalizedClinicalNote` containing:

- normalized clinical narrative
- source ClinicalNote reference
- normalization specification version
- required runtime metadata

The resulting artifact becomes the canonical normalized representation used throughout the remainder of the runtime pipeline.

---

# Traceability

Every `NormalizedClinicalNote` must remain traceable back to its originating `ClinicalNote`.

The artifact should therefore contain a stable reference to the source clinical observation.

Example:

```
ClinicalNote

↓

NormalizedClinicalNote

↓

RetrievalResult

↓

ReasoningContext

↓

CodingRecommendation

↓

ClinicalDecision
```

Every downstream runtime artifact remains traceable to the original physician-authored observation.

---

# Normalization Versioning

Normalization specification version forms part of the runtime artifact.

Example:

```
NormalizedClinicalNote

normalization_version = "1.0"
```

This version identifies the deterministic normalization rules used to produce the artifact.

Operational deployment information—including service version, Git commit, deployment identifier, or runtime environment—is not part of the business artifact and belongs in operational audit records.

---

# Persistence Boundary

NormalizationService depends on repository abstractions rather than storage technologies.

Example dependencies:

```
ClinicalNoteContentRepository

Clock

NormalizationRuleSet
```

The service must never depend directly upon:

```
SQLite

Filesystem

Cloud Blob Storage

Encryption implementation
```

Storage implementation remains an infrastructure concern.

---

# Dependencies

Allowed:

```
ClinicalNoteContentRepository

Normalization rule engine

PHI anonymizer

Clock abstraction

Domain validators
```

Not allowed:

```
Redis

Vector database

Embedding provider

LLM

CrewAI

LangGraph

Prompt templates

ICD taxonomy
```

Normalization must remain entirely deterministic and infrastructure-independent.

---

# Does Not Own

NormalizationService intentionally does not perform:

## Clinical interpretation

It does not:

- extract symptoms
- infer diagnoses
- classify conditions
- assign ICD codes
- generate recommendations

---

## Retrieval

It does not:

- generate embeddings
- perform vector search
- rank semantic candidates

Those responsibilities belong to RetrievalService.

---

## Workflow orchestration

It does not decide:

- cache lookup
- retrieval timing
- reasoning execution
- persistence

Those responsibilities belong to workflow orchestration.

---

# Determinism Classification

NormalizationService is fully deterministic.

Given:

```
Same ClinicalNote

+

Same clinical contents

+

Same normalization specification
```

the service must always produce the same `NormalizedClinicalNote`.

No probabilistic behavior is permitted.

---

# Testing Boundary

NormalizationService must be independently testable without:

- SQLite
- Redis
- Vector database
- LLM providers
- CrewAI
- LangGraph

Tests should verify:

- deterministic normalization
- deterministic PHI anonymization
- normalization version assignment
- source traceability
- repository interaction
- immutable artifact construction

---

# Future Replacement Flexibility

The following may change without affecting callers:

- storage implementation
- anonymization implementation
- normalization algorithm
- normalization rule engine
- encryption mechanism

The stable application boundary remains:

```
ClinicalNote

↓

NormalizationService

↓

NormalizedClinicalNote
```

---

# Architectural Role

`NormalizationService` establishes the deterministic preprocessing boundary of AEGIS.

It transforms immutable physician-authored clinical observations into standardized runtime artifacts suitable for semantic retrieval while preserving complete traceability to the original source.

By isolating preprocessing from retrieval and AI reasoning, the service ensures that downstream probabilistic components always operate on reproducible and deterministic input.