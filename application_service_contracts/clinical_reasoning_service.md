# Application Service Contract — ClinicalReasoningService

## Purpose

`ClinicalReasoningService` owns the business capability of transforming a bounded clinical evidence context into a structured clinical coding recommendation through a reasoning process.

Its responsibility is to answer:

> "Given the available clinical evidence, what ICD-11 coding recommendation should be proposed?"

The service produces recommendations only.

It never establishes clinical truth.

The reasoning process may be implemented using:

- CrewAI
- one or more LLMs
- deterministic reasoning engines
- future AI frameworks
- human-assisted reasoning systems

The implementation may evolve over time, but the business capability remains unchanged.

---

# Architectural Flow

`ClinicalReasoningService` sits downstream of retrieval and context assembly,
never in front of them:

```
RetrievalResult

        ↓

ContextAssembler

        ↓

ReasoningContext

        ↓

ClinicalReasoningService

        ↓

CodingRecommendation
```

Ownership along this flow is:

- `RetrievalService` owns retrieval and produces `RetrievalResult`.
- `ContextAssembler` owns curating `RetrievalResult` into the bounded
  `ReasoningContext` that crosses the reasoning boundary.
- `ClinicalReasoningService` only reasons over `ReasoningContext` — it never
  receives, constructs, or depends on `RetrievalResult` or `RetrievalCandidate`
  directly.
- `ReasoningProvider` (the CrewAI/LLM/agent-framework boundary described under
  Internal Architecture) produces raw, untrusted probabilistic output —
  structurally shaped, but not yet trusted.
- `ClinicalReasoningService` validates that output (schema validation plus the
  "no invented ICD codes outside ReasoningContext.candidates" business
  invariant) before any `CodingRecommendation` is constructed.
- `CodingRecommendation` is created only after validation succeeds; a failed
  validation must never produce a `CodingRecommendation`.

---

# Ownership

## Consumes

`ReasoningContext`

A deterministic and bounded evidence package prepared by `ContextAssembler`
from a `RetrievalResult`. `ClinicalReasoningService` never sees that
`RetrievalResult` — `ReasoningContext` is the only evidence input it depends
on. See Architectural Flow above.

The service never constructs `ReasoningContext` itself.

---

## Creates

`CodingRecommendation`

The service owns creation of the recommendation artifact.

Internally, structured output validation may be delegated to PydanticAI, but ownership of the business capability remains with `ClinicalReasoningService`.

The relationship is:

```
ReasoningContext

        ↓

ClinicalReasoningService

        ↓

CodingRecommendation
```

---

# Architectural Role

`ClinicalReasoningService` forms the probabilistic reasoning boundary of AEGIS.

It represents the point where deterministic evidence preparation transitions into probabilistic interpretation.

The service performs reasoning only.

It never determines clinical truth.

The complete authority chain is:

```
Clinical Evidence

        ↓

ReasoningContext

        ↓

ClinicalReasoningService

        ↓

CodingRecommendation

        ↓

Physician

        ↓

ClinicalDecision
```

---

# Primary Responsibilities

## 1. Clinical Reasoning

Interpret the bounded clinical evidence contained within `ReasoningContext`.

The service evaluates:

- clinical narrative
- candidate ICD concepts
- taxonomy context
- supporting evidence

to produce structured recommendations.

---

## 2. Recommendation Generation

Produce one or more candidate ICD-11 coding recommendations.

Recommendations may include:

- suggested ICD codes
- reasoning rationale
- supporting evidence references
- model confidence signal
- explanatory metadata

These recommendations remain advisory.

---

## 3. Structured Output Validation

Ensure reasoning outputs conform to the canonical `CodingRecommendation` contract.

Structured validation may include:

- schema validation
- automatic retry
- output correction
- validation failure handling

The service is responsible for ensuring downstream consumers receive valid business contracts.

---

## 4. Reasoning Execution

The internal reasoning strategy is implementation-specific.

Possible implementations include:

- CrewAI
- direct LLM invocation
- multi-agent collaboration
- deterministic rule engines
- future reasoning frameworks

The implementation is hidden behind the service boundary.

---

# Internal Architecture

A typical implementation may resemble:

```
ReasoningContext

        ↓

Prompt Provider

        ↓

CrewAI

        ↓

LLM

        ↓

PydanticAI Validation

        ↓

CodingRecommendation
```

Each component is replaceable without changing the service contract.

The current implementation names this replaceable boundary `ReasoningProvider`
— an abstraction `ClinicalReasoningService` depends on, implemented by
whatever combination of CrewAI, a direct LLM call, or a future framework is
in use. `ReasoningProvider` returns raw, untrusted structured output;
`ClinicalReasoningService` (not `ReasoningProvider`) owns validating it into a
`CodingRecommendation`.

---

# Prompt Boundary

`ClinicalReasoningService` may request prompts required for its reasoning capability.

However, it does not own prompt definitions.

Prompt ownership belongs to the prompt management layer.

The separation is:

```
Prompt Management

↓

Prompt Templates


ClinicalReasoningService

↓

Prompt Selection


CrewAI

↓

Prompt Execution
```

This keeps reasoning behavior independent from prompt storage.

---

# CrewAI Boundary

CrewAI exists solely to execute the reasoning process.

CrewAI may:

- analyze evidence
- compare candidate concepts
- generate reasoning
- construct recommendation candidates

CrewAI must never:

- perform workflow routing
- update persistence
- access infrastructure directly
- decide application flow
- establish clinical truth

CrewAI is an internal implementation detail of the service.

---

# Confidence Boundary

The service may expose a model-generated confidence signal.

This represents only the reasoning model's internal self-assessment.

It must never be interpreted as:

- physician confidence
- clinical certainty
- diagnostic probability
- workflow authority

The confidence signal exists solely as supplemental information.

---

# Determinism Classification

`ClinicalReasoningService` is intentionally probabilistic.

Identical inputs may produce different recommendations depending on the reasoning implementation.

Rather than enforcing deterministic outputs, AEGIS emphasizes reproducible reasoning environments.

Operational metadata should capture:

- model version
- prompt version
- reasoning configuration
- temperature
- context version
- execution timestamp

This enables reproducibility without assuming deterministic model behavior.

---

# Dependencies

Allowed:

```
ReasoningContext

Prompt Provider

CrewAI

LLM Provider

PydanticAI

Reasoning configuration
```

---

Not allowed:

```
SQLite

Redis

VectorStore

EmbeddingProvider

ClinicalDecisionRepository

Workflow routing

Patient identity systems
```

---

# Historical Decision Boundary

The service must not access previous physician-approved clinical decisions.

Historical decisions risk introducing confirmation bias into reasoning.

Each recommendation should be generated independently from the available clinical evidence.

The service reasons only over the supplied `ReasoningContext`.

---

# Does Not Own

## Clinical Truth

The service does not create:

- ClinicalDecision
- physician approval
- authoritative diagnoses

---

## Workflow

The service does not determine:

- retry policies
- workflow routing
- cache usage
- persistence timing

Those responsibilities belong to LangGraph and application orchestration.

---

## Retrieval

The service does not:

- generate embeddings
- query vector databases
- retrieve ICD concepts

Those responsibilities belong to `RetrievalService`.

---

## Context Preparation

The service does not:

- curate evidence
- select candidates
- perform token budgeting

Those responsibilities belong to `ContextAssembler`.

---

# Testing Boundary

`ClinicalReasoningService` should be independently testable.

Tests should verify:

- reasoning invocation
- prompt selection
- schema validation
- failure handling
- recommendation construction
- retry behavior
- replacement of reasoning implementations

Reasoning implementations should be mockable.

The service contract should remain stable regardless of which reasoning framework is used.

---

# Future Replacement Flexibility

The following may change independently:

- CrewAI
- LLM provider
- prompt templates
- reasoning framework
- validation library

The stable contract remains:

```
ReasoningContext

        ↓

ClinicalReasoningService

        ↓

CodingRecommendation
```

---

# Architectural Philosophy

`ClinicalReasoningService` is the probabilistic reasoning capability of AEGIS.

It transforms bounded clinical evidence into structured recommendations while deliberately avoiding ownership of clinical truth.

By separating reasoning from physician authority, AEGIS ensures that artificial intelligence remains an assistive capability rather than an authoritative decision maker.

Recommendations inform clinical practice.

Only physicians establish clinical truth.