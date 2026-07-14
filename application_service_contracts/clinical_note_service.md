# Application Service Contract — ClinicalNoteService

## Purpose

`ClinicalNoteService` is responsible for creating and establishing the lifecycle of an immutable `ClinicalNote` domain artifact.

It represents the application boundary where externally submitted clinical observations transition from untrusted ingress data into a validated, identifiable, and persistable domain object.

The service does not interpret clinical information, perform AI reasoning, normalize content, or determine medical meaning.

Its sole responsibility is ensuring that a clinical observation enters AEGIS as a stable source artifact from which all downstream deterministic and probabilistic processing can be derived.

---

# Ownership

## Creates

`ClinicalNote`

The service owns construction of the domain object.

External interfaces such as FastAPI, message consumers, or batch ingestion mechanisms provide submission data but do not directly instantiate the domain artifact.

The creation boundary is:

```
External Submission

        ↓

ClinicalNoteService

        ↓

ClinicalNote
```

This prevents infrastructure-specific ingress layers from becoming domain object owners.

---

## Consumed By

After creation, `ClinicalNote` may be consumed by:

- NormalizationService
- Workflow orchestration
- Retrieval preparation
- Audit systems
- Persistence-related workflows

Downstream components must never mutate or recreate the original `ClinicalNote`.

---

# Lifetime

`ClinicalNote` is immutable and long-lived.

It represents the exact clinical observation submitted at a specific point in time.

The artifact remains stable throughout the entire lifecycle of the clinical case.

Any later correction, enrichment, or transformation must produce a separate artifact rather than modifying the original object.

Example:

```
ClinicalNote

        +

NormalizedClinicalNote

        +

ClinicalDecision
```

are separate immutable representations with independent responsibilities.

---

# Primary Responsibilities

## 1. Domain Object Construction

The service transforms an external submission into a valid `ClinicalNote`.

Responsibilities include:

- generating clinical note identity
- assigning creation metadata
- validating required domain information
- constructing immutable representation

---

## 2. Persistence Coordination

ClinicalNote creation and persistence are treated as a single successful operation.

The service guarantees:

```
Successful ClinicalNote creation

        implies

ClinicalNote exists in durable storage
```

The service coordinates persistence through a repository abstraction.

It does not directly interact with database technologies.

---

## 3. Lifecycle Establishment

The service establishes:

- artifact identity
- creation timestamp
- source metadata
- storage reference lifecycle

It does not manage downstream processing state.

---

# Persistence Boundary

ClinicalNoteService depends on:

```
ClinicalNoteRepository
```

not:

```
SQLite
PostgreSQL
Filesystem
```

The dependency direction is:

```
ClinicalNoteService

        ↓

ClinicalNoteRepository

        ↓

Storage Implementation
```

This allows the persistence mechanism to change without affecting application behavior.

---

# Dependencies

Allowed:

```
ClinicalNoteRepository

Domain validators

Identifier generator

Clock abstraction
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
```

ClinicalNote creation must remain deterministic and independent from AI infrastructure.

---

# Does Not Own

ClinicalNoteService does not own:

## Clinical interpretation

It does not:

- extract symptoms
- assign ICD codes
- generate recommendations
- perform reasoning

---

## Normalization

It does not:

- anonymize PHI
- clean text
- generate normalized representations

That responsibility belongs to:

```
NormalizationService
```

---

## Workflow orchestration

It does not decide:

- when retrieval happens
- whether reasoning runs
- whether human review is required

That belongs to:

```
LangGraph orchestration
```

---

## Software execution history

ClinicalNote does not contain:

- ClinicalNoteService version
- implementation version
- deployment metadata

Software lineage belongs to operational audit records.

Clinical truth and execution history remain separate concepts.

---

# Determinism Classification

ClinicalNoteService is deterministic.

Given:

```
Same submission

+

Same validation rules

+

Same identity generation strategy

```

the service produces the same type of immutable artifact.

It contains no probabilistic operations.

---

# Testing Boundary

The service must be independently testable without:

- SQLite
- Redis
- Vector database
- LLM providers
- LangGraph runtime

Example:

```
ClinicalNoteSubmission

        ↓

ClinicalNoteService

        ↓

ClinicalNote

        ↓

Repository verification
```

Tests should verify:

- identity creation
- immutable construction
- persistence invocation
- invalid input rejection
- repository interaction

---

# Future Replacement Flexibility

The following can change without affecting callers:

- SQLite implementation
- PostgreSQL migration
- external EHR integration
- UUID strategy
- storage mechanism
- ingestion channel

The stable boundary remains:

```
ClinicalNoteSubmission

        ↓

ClinicalNoteService

        ↓

ClinicalNote
```

---

# Architectural Role

`ClinicalNoteService` establishes the first trusted artifact boundary inside AEGIS.

It converts external clinical input into an immutable source artifact that becomes the reference point for every downstream deterministic transformation and AI-assisted reasoning process.

The service ensures that AEGIS always reasons from a stable clinical observation rather than transient request data.