# Application Service Contract — PersistenceService

## Purpose

`PersistenceService` owns the business capability of materializing authoritative clinical truth into durable storage.

Its responsibility is:

> "Given an authoritative ClinicalDecision, ensure that institutional clinical truth is durably preserved."

PersistenceService does not create truth.

It preserves truth that has already been established by physician approval.

---

# Architectural Role

PersistenceService represents the boundary between:

```
Authoritative Clinical Truth

↓

Durable Storage Representation
```

The service translates:

```
ClinicalDecision

↓

Durable Records
```

Examples:

```
ClinicalDecision

↓

ClinicalDecision Repository

↓

Audit Records

↓

Patient Clinical History
```

The service owns durable persistence orchestration, not business interpretation.

---

# Ownership

## Consumes

### ClinicalDecision

The immutable authoritative clinical decision produced by `ClinicalDecisionService`.

This is the only business artifact required to establish persistence.

PersistenceService assumes:

- physician approval has already occurred.
- recommendation validation has already occurred.
- the decision represents accepted institutional truth.

PersistenceService does not re-evaluate clinical correctness.

---

### Optional Persistence Context

Operational metadata may optionally be supplied when required.

Examples:

- correlation identifier
- request identifier
- transaction metadata

These are operational concerns, not business truth.

---

# Produces

## PersistenceResult

A structured result describing the durable persistence outcome.

Typical fields:

- success status
- transaction identifier
- persisted entities
- persistence timestamp
- failure information if applicable

This enables:

- observability.
- debugging.
- operational monitoring.
- deterministic workflow handling.

PersistenceResult describes durable storage outcome only.

It does not describe:

- cache status.
- retrieval status.
- AI reasoning status.
- workflow state.

---

# Primary Responsibilities

## 1. Durable Persistence

Persist authoritative clinical truth into system-of-record storage.

Examples:

- ClinicalDecision records.
- patient clinical history.
- physician approval records.
- audit history.

---

## 2. Repository Coordination

Coordinate required durable repositories needed to preserve clinical truth.

Examples:

```
ClinicalDecisionRepository

AuditRepository

PatientClinicalRecordRepository
```

Repositories own technology details.

PersistenceService owns the persistence workflow.

---

## 3. Transaction Coordination

Coordinate durable persistence operations required to preserve consistency.

Example:

```
BEGIN transaction

↓

Persist ClinicalDecision

↓

Persist audit record

↓

Persist patient clinical history

↓

COMMIT
```

Transaction handling belongs to the durable persistence boundary.

---

# Cache Boundary

## CacheService Owns Cache Persistence

Cache updates are intentionally outside PersistenceService ownership.

The architecture separates:

```
Durable Truth

↓

PersistenceService

```

from:

```
Knowledge Reuse

↓

CacheService
```

The cache is a derived deterministic knowledge reuse mechanism.

It is not part of durable persistence.

---

The workflow orchestration layer owns ordering:

```
ClinicalDecision

↓

PersistenceService.persist()

↓

Successful durable commit

↓

CacheService.store()
```

This ordering ensures:

- only persisted truth enters the cache.
- failed persistence cannot create reusable knowledge.
- cache lifecycle remains independent from storage technology.

---

PersistenceService must never:

- call CacheService.
- write Redis directly.
- generate cache keys.
- determine cache invalidation policy.
- coordinate cache refresh.

---

# Failure Handling

PersistenceService distinguishes durable storage failures.

## Durable Storage Failure

Example:

```
SQLite transaction failure
```

Result:

```
Persistence fails
```

The ClinicalDecision is not considered durably preserved.

The caller/workflow decides retry or recovery behavior.

---

## Cache Failure

Not handled by PersistenceService.

Example:

```
SQLite success

↓

CacheService failure
```

Result:

Durable truth remains valid.

Cache recovery is handled by the cache subsystem.

A cache failure must never invalidate authoritative clinical truth.

---

# Determinism

PersistenceService should be deterministic.

Given:

```
Same ClinicalDecision

+

Same durable storage state
```

it should produce the same persistence outcome.

This supports:

- replay.
- recovery.
- auditing.
- testing.

PersistenceService does not introduce:

- probabilistic decisions.
- AI reasoning.
- semantic matching.

---

# Repository Boundary

PersistenceService should not directly depend on database technologies.

It depends on repository abstractions.

Examples:

```
ClinicalDecisionRepository

AuditRepository

PatientClinicalRecordRepository
```

The following are forbidden dependencies:

```
SQLite implementation details

Redis clients

Vector databases

Embedding providers

LLM clients
```

Repositories own infrastructure concerns.

PersistenceService owns durable persistence behavior.

---

# Does Not Own

## Business Decisions

PersistenceService does not:

- interpret ICD codes.
- evaluate recommendations.
- classify physician decisions.
- modify ClinicalDecision contents.

---

## AI Systems

PersistenceService does not know:

- LLMs.
- CrewAI.
- prompts.
- reasoning workflows.
- confidence scores.

---

## Retrieval Systems

PersistenceService does not know:

- embeddings.
- vector databases.
- semantic search.
- retrieval candidates.

---

## Cache Systems

PersistenceService does not own:

- Redis.
- cache keys.
- cache expiration.
- cache invalidation.
- knowledge reuse.

---

## Workflow Management

PersistenceService does not own:

- LangGraph execution.
- human review routing.
- workflow retries.
- orchestration ordering.

---

# Testing Boundary

PersistenceService should be independently testable.

Tests should verify:

- repository coordination.
- durable persistence behavior.
- transaction handling.
- failure propagation.
- deterministic persistence results.

Tests should not require:

- Redis.
- vector databases.
- LLM providers.
- CrewAI.
- LangGraph.

Infrastructure implementations should be replaceable through repository abstractions.

---

# Future Replacement Flexibility

The following may change:

- SQLite.
- PostgreSQL.
- cloud databases.
- audit storage systems.
- event storage systems.

The stable capability remains:

```
ClinicalDecision

↓

PersistenceService

↓

Institutional Durable Knowledge
```

---

# Architectural Philosophy

PersistenceService exists because truth and storage are different concepts.

`ClinicalDecision` creates authoritative clinical truth.

`PersistenceService` preserves that truth.

`CacheService` reuses previously established truth.

These responsibilities must remain separate.

The system may replace:

- databases.
- caches.
- storage technologies.

The meaning of the persisted clinical decision must remain unchanged.

AEGIS therefore maintains:

- reproducibility.
- auditability.
- storage independence.
- deterministic knowledge reuse.
- separation between truth creation, truth preservation, and truth reuse.