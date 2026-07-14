# Application Service Contract — PersistenceService

## Purpose

`PersistenceService` owns the business capability of materializing authoritative clinical truth into all required durable and derived storage representations while preserving consistency.

Its responsibility is:

> "Given an authoritative ClinicalDecision, ensure that institutional clinical truth is durably preserved across required storage projections."

PersistenceService does not create truth.

It preserves truth that has already been established by physician approval.

---

# Architectural Role

PersistenceService represents the boundary between:

```
Business Truth

↓

Physical Storage Representations
```

The service translates:

```
ClinicalDecision

↓

Durable Records

+

Derived Projections
```

Examples:

```
ClinicalDecision

↓

ClinicalDecision Repository

↓

Patient Extracted Codes

↓

Audit Records

↓

Cache Projection
```

The service owns persistence orchestration, not business interpretation.

---

# Ownership

## Consumes

### ClinicalDecision

The immutable authoritative clinical decision produced by `ClinicalDecisionService`.

This is the only business artifact required to establish persistence.

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

A structured result describing the persistence outcome.

Typical fields:

- success status
- transaction identifier
- persisted entities
- projection status
- timestamps
- failure information if applicable

This enables:

- observability.
- debugging.
- operational monitoring.
- deterministic workflow handling.

---

# Primary Responsibilities

## 1. Durable Persistence

Persist authoritative clinical truth into system-of-record storage.

Examples:

- clinical decision records.
- patient extracted ICD codes.
- audit history.

---

## 2. Projection Management

Create and maintain derived representations required for application performance.

Examples:

```
ClinicalDecision

↓

Redis clinical memory projection
```

Derived projections must never become the source of truth.

---

## 3. Transaction Coordination

Coordinate persistence operations required to preserve consistency.

Example:

```
BEGIN transaction

↓

Persist ClinicalDecision

↓

Persist extracted ICD codes

↓

Persist audit records

↓

COMMIT

↓

Update derived projections
```

---

# Repository Boundary

PersistenceService should not directly depend on database technologies.

It depends on repository abstractions.

Examples:

```
ClinicalDecisionRepository

PatientExtractedCodeRepository

AuditRepository

ClinicalCacheRepository
```

Repositories own technology details.

PersistenceService owns orchestration.

---

# Redis Projection Boundary

Redis is considered a derived projection.

PersistenceService owns:

- determining when cache updates occur.
- generating required persistence projections.
- coordinating cache repository operations.

It does not treat Redis as authoritative storage.

Authority remains:

```
SQLite / durable storage

↓

Redis projection
```

---

# Failure Handling

PersistenceService must distinguish:

## Durable Storage Failure

Example:

```
SQLite transaction failure
```

Result:

Persistence operation fails.

No authoritative truth should be considered persisted.

---

## Derived Projection Failure

Example:

```
SQLite success

↓

Redis failure
```

Result:

Durable truth remains committed.

The projection should be:

- marked incomplete,
- retried,
- reconciled later.

Derived storage failure must never invalidate authoritative clinical truth.

---

# Determinism

PersistenceService should be deterministic.

Given:

```
Same ClinicalDecision

+

Same storage state
```

it should produce the same persistence outcome.

This supports:

- replay.
- recovery.
- auditing.
- testing.

---

# Does Not Own

## Business Decisions

PersistenceService does not:

- interpret ICD codes.
- evaluate recommendations.
- classify physician decisions.

---

## AI Systems

PersistenceService does not know:

- LLMs.
- CrewAI.
- prompts.
- reasoning workflows.

---

## Retrieval Systems

PersistenceService does not know:

- embeddings.
- vector databases.
- semantic search.

---

## Workflow Management

PersistenceService does not own:

- LangGraph execution.
- retries at workflow level.
- human review routing.

---

# Testing Boundary

PersistenceService should be independently testable.

Tests should verify:

- repository coordination.
- transaction handling.
- projection behavior.
- failure recovery.
- deterministic persistence results.

Infrastructure implementations should be replaceable through repository abstractions.

---

# Future Replacement Flexibility

The following may change:

- SQLite.
- PostgreSQL.
- Redis.
- MongoDB.
- Cloud storage.
- Event streaming systems.

The stable capability remains:

```
ClinicalDecision

↓

PersistenceService

↓

Institutional Knowledge Storage
```

---

# Architectural Philosophy

PersistenceService exists because truth and storage are different concepts.

`ClinicalDecision` creates authoritative clinical truth.

`PersistenceService` preserves that truth.

The service ensures that AEGIS remains:

- reproducible.
- auditable.
- storage-independent.
- resilient to infrastructure changes.

The system may replace databases, caches, or storage technologies in the future.

The meaning of the persisted clinical decision must remain unchanged.