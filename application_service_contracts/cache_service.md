# Application Service Contract — CacheService

## Purpose

`CacheService` is responsible for the deterministic reuse of previously physician-approved clinical decisions.

It establishes the runtime knowledge reuse boundary of AEGIS by determining whether a normalized clinical observation has already been reviewed and approved by a physician.

Unlike a traditional performance cache, the primary purpose of `CacheService` is to reuse established clinical truth rather than simply reduce computation time.

Performance improvement is a beneficial consequence, not its architectural purpose.

---

# Ownership

## Consumes

`NormalizedClinicalNote`

The service accepts only canonical normalized clinical observations.

It never operates directly on raw physician-authored notes.

---

## Produces

One of two deterministic outcomes:

```
Cache Hit

↓

ClinicalDecision
```

or

```
Cache Miss

↓

No ClinicalDecision
```

The service never produces AI recommendations or partial decisions.

---

# Architectural Role

`CacheService` establishes the deterministic knowledge reuse boundary of AEGIS.

Its purpose is to recognize when an identical normalized clinical observation has already resulted in a physician-approved clinical decision.

When such a decision exists, downstream semantic retrieval and AI reasoning become unnecessary.

---

# Primary Responsibilities

## 1. Canonical Identity Generation

The service derives a deterministic cache identity from the normalized clinical observation.

Identity generation is based upon the canonical normalized representation rather than the original physician wording.

Conceptually:

```
NormalizedClinicalNote

↓

Canonical Representation

↓

SHA-256

↓

Cache Key
```

The cache key therefore represents the semantic identity established by deterministic normalization.

---

## 2. Knowledge Lookup

The service determines whether physician-approved clinical truth already exists for the normalized observation.

The lookup is entirely deterministic.

No similarity search, ranking, or probabilistic matching is performed.

---

## 3. Knowledge Storage

Following successful physician approval and durable persistence, the service stores the resulting `ClinicalDecision` for future deterministic reuse.

The service never stores provisional information.

---

# Semantic Identity

Normalization establishes semantic identity.

If two independently authored clinical observations produce the same canonical normalized representation under the same normalization specification, they are considered semantically equivalent for deterministic processing.

Example:

```
Clinical Note A

↓

Normalization

↓

Canonical Representation

↑

Normalization

↓

Clinical Note B
```

Both observations therefore generate the same cache identity.

This allows previously approved clinical decisions to be safely reused for future equivalent observations.

---

# What Is Cached

The cache stores only physician-approved clinical truth.

Example:

```
SHA-256(normalized observation)

↓

ClinicalDecision
```

The cache intentionally does not contain:

- CodingRecommendation
- AI output
- confidence scores
- retrieval candidates
- embeddings
- prompt context
- LLM responses

This prevents probabilistic output from becoming deterministic system knowledge.

---

# Persistence Boundary

CacheService depends upon an abstract cache repository.

Example:

```
ClinicalDecisionCacheRepository
```

The service must never depend directly upon:

```
Redis

KeyDB

Memcached

SQLite

Cloud cache implementations
```

The underlying technology may change without affecting application behavior.

---

# Dependencies

Allowed:

```
ClinicalDecisionCacheRepository

Hash generator

Clock abstraction
```

Not allowed:

```
SQLite

Vector database

Embedding provider

LLM

CrewAI

LangGraph

Prompt templates
```

---

# Does Not Own

CacheService intentionally does not perform:

## Clinical reasoning

It does not:

- generate recommendations
- interpret symptoms
- infer diagnoses
- rank ICD concepts

---

## Retrieval

It does not:

- generate embeddings
- perform vector search
- retrieve taxonomy entries

---

## Persistence

The service does not determine when cache updates occur.

Cache updates occur only after successful persistence of a physician-approved `ClinicalDecision`.

Persistence ordering remains the responsibility of workflow orchestration.

---

# Determinism Classification

CacheService is fully deterministic.

Given:

```
Same NormalizedClinicalNote

+

Same normalization specification

+

Same physician-approved cache contents
```

the service must always produce the same lookup result.

No probabilistic behavior is permitted.

---

# Testing Boundary

CacheService must be independently testable without:

- Redis
- SQLite
- Vector database
- LLM providers
- CrewAI
- LangGraph

Tests should verify:

- deterministic cache key generation
- cache hit detection
- cache miss detection
- correct storage behavior
- repository interaction
- prevention of non-approved artifacts entering the cache

---

# Future Replacement Flexibility

The following may change without affecting callers:

- Redis implementation
- cache technology
- hash algorithm
- storage optimization
- expiration strategy

The stable application boundary remains:

```
NormalizedClinicalNote

↓

CacheService

↓

ClinicalDecision | Cache Miss
```

---

# Architectural Philosophy

`CacheService` is not a performance optimization layer.

It is a deterministic clinical knowledge reuse mechanism.

Normalization establishes semantic identity.

CacheService establishes whether physician-approved clinical truth already exists for that identity.

Together they allow AEGIS to become increasingly deterministic as physician-approved knowledge accumulates over time while preserving complete separation between deterministic knowledge reuse and probabilistic AI reasoning.