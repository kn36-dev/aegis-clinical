# Application Service Contract — ContextAssembler

## Purpose

`ContextAssembler` is responsible for transforming deterministic clinical artifacts and retrieved evidence into a bounded, structured reasoning input suitable for downstream clinical reasoning.

Its primary responsibility is not formatting. Its responsibility is controlling the information boundary between deterministic application components and probabilistic reasoning systems.

The service answers:

> "What information should the reasoning system be allowed to consider?"

It does not answer:

> "What clinical conclusion should be reached?"

---

# Ownership

## Consumes

`ClinicalNote`

The originating clinical observation artifact.

and:

`RetrievalResult`

The bounded collection of semantically retrieved ICD-11 candidate concepts.

The service does not directly access retrieval infrastructure or source storage.

---

## Creates

`ReasoningContext`

The service owns construction of the reasoning boundary object.

The creation flow is:

```
ClinicalNote

+

RetrievalResult

        ↓

ContextAssembler

        ↓

ReasoningContext
```

`ClinicalReasoningService` consumes `ReasoningContext` but does not construct it.

---

# Architectural Role

`ContextAssembler` forms the final deterministic preparation layer before probabilistic reasoning.

It transforms:

```
Clinical Evidence

        ↓

Bounded Reasoning Context

        ↓

AI Reasoning
```

This prevents downstream reasoning components from directly controlling their own evidence selection.

The reasoning system receives curated evidence rather than unrestricted access to application data.

---

# Primary Responsibilities

## 1. Evidence Selection

The service selects the clinically relevant information required for reasoning.

This may include:

- anonymized clinical narrative
- normalized clinical representations
- ICD-11 candidate concepts
- taxonomy hierarchy context
- required metadata for explanation

The service intentionally avoids forwarding unnecessary information.

---

## 2. Candidate Curation

The service performs deterministic preparation of retrieved candidates.

Allowed operations include:

- duplicate removal
- malformed candidate filtering
- candidate limit enforcement
- deterministic ordering
- metadata selection

The service does not perform clinical ranking.

---

## 3. Context Construction

The service creates a structured `ReasoningContext` containing only information approved for downstream reasoning.

The context should optimize for:

- relevance
- minimal sufficient information
- token efficiency
- explainability
- deterministic reproducibility

---

## 4. Information Boundary Enforcement

The service prevents unnecessary or potentially biasing information from entering probabilistic reasoning.

Examples of excluded information:

- retrieval similarity scores
- cache contents
- previous physician decisions
- patient identity information
- infrastructure metadata

---

# ReasoningContext Relationship

`ReasoningContext` represents the controlled input provided to clinical reasoning.

The relationship is:

```
ClinicalNote

        +

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

---

# Prompt Boundary

ContextAssembler does not own prompts.

It produces reasoning data, not instructions.

The separation is:

```
ContextAssembler

        ↓

"What information should the model see?"


Prompt Layer

        ↓

"How should the model behave?"
```

Prompt templates remain owned by the prompt management layer.

---

# CrewAI Boundary

ContextAssembler does not know about CrewAI.

It must remain valid regardless of the reasoning implementation.

Possible consumers include:

- CrewAI
- LangChain agents
- custom LLM workflows
- deterministic reasoning engines
- future AI systems

The service exists because AEGIS requires controlled reasoning inputs, not because a specific AI framework exists.

---

# Ranking Boundary

ContextAssembler does not perform clinical ranking.

It may perform deterministic evidence preparation.

Allowed:

```
RetrievalResult

↓

Remove duplicates

↓

Limit candidates

↓

Order deterministically

↓

ReasoningContext
```

Not allowed:

```
Candidate A is medically more likely than Candidate B
```

Clinical interpretation belongs to `ClinicalReasoningService`.

---

# Token and Context Optimization

ContextAssembler owns deterministic context budgeting.

Allowed:

- candidate count limits
- deterministic truncation
- unnecessary metadata removal
- hierarchy depth limitation
- representation length constraints

Not allowed:

- LLM summarization
- AI-based compression
- semantic rewriting

The context preparation phase must remain deterministic.

---

# Determinism Classification

`ContextAssembler` is fully deterministic.

Given:

```
Same ClinicalNote

+

Same RetrievalResult

+

Same configuration
```

the service must produce:

```
Same ReasoningContext
```

This enables:

- reproducible evaluation
- workflow replay
- debugging
- AI output analysis

---

# Dependencies

Allowed:

```
Domain contracts

Context configuration

Deterministic transformation utilities
```

---

Not allowed:

```
VectorStore

EmbeddingProvider

Redis

SQLite

LLM

CrewAI

Prompt execution

LangGraph
```

ContextAssembler should only operate on already-produced domain artifacts.

---

# Does Not Own

## Clinical Reasoning

The service does not:

- interpret evidence
- diagnose conditions
- choose ICD codes
- generate recommendations

---

## Prompt Engineering

The service does not:

- define system prompts
- define agent roles
- control LLM behavior

---

## Retrieval

The service does not:

- generate embeddings
- query vector databases
- retrieve ICD concepts

---

## Clinical Truth

The service does not create:

- ClinicalDecision
- physician-approved outcomes

---

# Testing Boundary

ContextAssembler must be independently testable without:

- LLM providers
- CrewAI
- vector databases
- Redis
- workflow orchestration

Tests should verify:

- deterministic context construction
- candidate filtering
- ordering behavior
- excluded information enforcement
- token budgeting behavior
- stable transformation from artifacts into reasoning context

---

# Future Replacement Flexibility

The following may change without affecting callers:

- CrewAI
- LLM provider
- prompt strategy
- agent architecture
- reasoning framework

The stable contract remains:

```
ClinicalNote

+

RetrievalResult

        ↓

ContextAssembler

        ↓

ReasoningContext
```

---

# Architectural Philosophy

`ContextAssembler` is the deterministic reasoning gateway of AEGIS.

It does not make clinical decisions.

It controls the evidence boundary from which clinical decisions may be reasoned.

By separating context preparation from reasoning execution, AEGIS ensures that:

- retrieval remains independent from interpretation
- reasoning remains bounded by explicit evidence
- AI systems cannot access unnecessary application state
- future reasoning technologies can replace current implementations without changing upstream architecture

The quality of AI reasoning depends not only on the intelligence of the model, but on the quality and discipline of the context provided to it.