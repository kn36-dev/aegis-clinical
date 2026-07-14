# Application Service Contract — RetrievalService

## Purpose

`RetrievalService` is responsible for retrieving semantically relevant ICD-11 concepts from the configured clinical knowledge index based on a normalized clinical observation.

It represents the semantic retrieval boundary of AEGIS, transforming a deterministic `NormalizedClinicalNote` into a bounded collection of candidate clinical concepts that can be consumed by downstream reasoning components.

The service answers:

> "Which concepts are semantically similar to this clinical observation?"

It does not answer:

> "Which concept is clinically correct?"

Clinical interpretation, ranking, diagnosis, and final ICD selection belong to downstream reasoning boundaries.

---

# Ownership

## Consumes

`RetrievalRequest`

The request represents retrieval intent and contains the information required to execute retrieval.

Typical information may include:

- normalized clinical artifact reference
- retrieval configuration
- candidate limits
- similarity constraints
- retrieval mode

The service executes the requested retrieval operation but does not define workflow policy.

---

## Creates

`RetrievalResult`

The service owns translation from provider-specific retrieval output into canonical AEGIS domain objects.

The creation boundary is:

```
RetrievalRequest

        ↓

RetrievalService

        ↓

RetrievalResult
```

The underlying retrieval provider does not own AEGIS runtime contracts.

---

# Architectural Role

`RetrievalService` forms the boundary between semantic search infrastructure and downstream clinical reasoning.

The service transforms:

```
NormalizedClinicalNote

        ↓

Semantic Query Representation

        ↓

Knowledge Retrieval

        ↓

RetrievalResult
```

The resulting artifact represents bounded evidence, not a medical conclusion.

---

# Primary Responsibilities

## 1. Query Representation Generation

The service transforms the retrieval request into a semantic query representation suitable for the configured retrieval mechanism.

This may include:

- embedding generation
- query preprocessing required by the retrieval provider

The exact embedding technology is hidden behind an abstraction.

Example:

```
NormalizedClinicalNote

        ↓

EmbeddingProvider

        ↓

Vector Representation
```

---

## 2. Semantic Knowledge Retrieval

The service retrieves semantically similar ICD-11 concepts from the configured knowledge index.

The retrieval mechanism may use:

- vector databases
- similarity search engines
- future retrieval technologies

The underlying implementation remains replaceable.

---

## 3. Provider Translation

The service translates provider-specific responses into canonical runtime contracts.

Example:

```
Vector Search Response

{
    id,
    score,
    metadata
}

        ↓

RetrievalService

        ↓

RetrievalResult

{
    RetrievalCandidate[]
}
```

Downstream consumers should not require knowledge of the retrieval technology.

---

## 4. Bounded Evidence Production

The service produces a bounded collection of candidate concepts.

The result should contain enough information for downstream reasoning without exposing unnecessary infrastructure details.

---

# RetrievalResult Relationship

`RetrievalResult` represents semantic evidence.

It does not represent:

- diagnosis
- clinical confidence
- final ICD selection
- physician decision

The relationship is:

```
RetrievalResult

        provides evidence for

ReasoningContext

        which supports

ClinicalReasoningService

        which produces

CodingRecommendation
```

---

# Ranking Boundary

RetrievalService does not perform clinical ranking.

The service may preserve retrieval-provider ordering based on semantic similarity.

Example:

Allowed:

```
Candidate A
similarity score: 0.91

Candidate B
similarity score: 0.86
```

Not allowed:

```
Candidate A is clinically more appropriate because...
```

Clinical interpretation belongs outside retrieval.

---

# Determinism Classification

RetrievalService is deterministic under a controlled retrieval environment.

Identical retrieval results require:

```
Same NormalizedClinicalNote

+

Same normalization specification

+

Same embedding model version

+

Same vector index state

+

Same retrieval configuration
```

Therefore:

```
Same environment

↓

Same RetrievalResult
```

is expected.

However, retrieval reproducibility depends on knowledge index state and model versions.

---

# Dependencies

Allowed:

```
EmbeddingProvider

VectorStore

Retrieval configuration

Domain validators
```

Optional:

```
TaxonomyRepository
```

if additional deterministic metadata enrichment is required.

---

Not allowed:

```
Redis

ClinicalDecision storage

LLM

CrewAI

Prompt templates

LangGraph

Workflow state management
```

Retrieval must remain independent from reasoning and decision-making.

---

# Configuration Ownership

Retrieval behavior is defined by `RetrievalRequest`.

Examples:

- top_k
- similarity threshold
- retrieval mode
- query constraints

The service executes retrieval according to the request.

It does not own workflow-specific retrieval policy.

The boundary is:

```
RetrievalRequest

"What retrieval behavior is requested?"

        ↓

RetrievalService

"How is retrieval performed?"
```

---

# Does Not Own

## Clinical interpretation

RetrievalService does not:

- diagnose conditions
- infer medical meaning
- select ICD codes
- determine correctness

---

## Ranking and reasoning

RetrievalService does not:

- determine best candidate
- explain clinical relevance
- compare competing diagnoses
- generate recommendations

---

## Workflow orchestration

RetrievalService does not know:

- whether cache lookup occurred
- whether human review is required
- whether reasoning should execute
- current workflow state

---

## Clinical truth

RetrievalService never produces:

- ClinicalDecision
- physician-approved outcome

It only produces evidence.

---

# Replayability

RetrievalService supports deterministic replay when executed under a controlled retrieval environment.

A replayable execution requires preservation of:

- NormalizedClinicalNote artifact
- embedding model version
- retrieval configuration
- vector index state
- taxonomy snapshot

This enables:

- evaluation
- debugging
- workflow replay
- retrieval quality analysis

---

# Testing Boundary

RetrievalService must be independently testable without:

- LangGraph
- CrewAI
- LLM providers
- Redis
- production vector infrastructure

Tests should verify:

- request handling
- embedding provider interaction
- vector store interaction
- provider response translation
- RetrievalResult construction
- bounded candidate generation

---

# Future Replacement Flexibility

The following may change without affecting callers:

- Upstash Vector
- pgvector
- Elasticsearch
- FAISS
- embedding model provider
- similarity algorithm

The stable application boundary remains:

```
RetrievalRequest

        ↓

RetrievalService

        ↓

RetrievalResult
```

Consumers depend only on canonical domain contracts.

---

# Architectural Philosophy

RetrievalService is the semantic evidence acquisition boundary of AEGIS.

It converts deterministic clinical observations into bounded knowledge candidates while preserving strict separation between retrieval and reasoning.

The retrieval subsystem answers:

> "Which concepts are nearby in semantic space?"

It never answers:

> "Which concept is correct?"

By maintaining this boundary, AEGIS can evolve retrieval technology independently while ensuring that probabilistic reasoning operates on transparent, bounded, and reproducible evidence.