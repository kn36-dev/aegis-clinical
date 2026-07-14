# Runtime Domain Contract — ReasoningContext

## Purpose

`ReasoningContext` represents the final deterministic evidence package provided to probabilistic reasoning systems.

It defines the explicit boundary between deterministic application processing and LLM-based reasoning.

The responsibility of `ReasoningContext` is not to determine the answer, but to define exactly what information the AI system is permitted to reason over.

---

## Architectural Position

The lifecycle is:

ClinicalNote

↓

NormalizedClinicalNote

↓

RetrievalRequest

↓

RetrievalResult

↓

Candidate Ranking / Context Assembly

↓

ReasoningContext

↓

LLM Reasoning

↓

CodingRecommendation

↓

ClinicalDecision

---

## Ownership

Created by:

`ContextAssembler`

The ContextAssembler is responsible for transforming retrieval outputs into a curated reasoning package.

Neither LangGraph nor CrewAI should decide what information reaches the LLM.

---

## Consumers

Consumed by:

- LLM reasoning services
- CrewAI agents
- evaluation harnesses
- LangGraph workflow state

---

## Core Responsibility

ReasoningContext answers:

"What evidence is this reasoning system allowed to consider?"

It provides:

- original clinical observation
- selected ICD taxonomy candidates
- semantic representations required for comparison
- contextual metadata required for grounded reasoning

---

## Required Information

### Clinical Reference

A reference to the originating clinical note.

The original note remains owned by the ClinicalNote contract.

---

### Curated Candidates

A bounded collection of ICD taxonomy candidates selected for reasoning.

Each candidate should contain:

- ICD code
- clinical title
- hierarchy context
- semantic representation text

The candidate list should contain enough information for reasoning without requiring direct access to retrieval infrastructure.

---

## Explicit Exclusions

ReasoningContext must not contain:

- prompt instructions
- LLM provider details
- API keys
- vector database information
- similarity scores
- confidence values
- workflow state
- final diagnosis
- physician decisions

Similarity ordering may be preserved internally, but similarity values should not automatically be exposed to the model because they may introduce ranking bias.

---

## Context Assembly Philosophy

ReasoningContext is a curated artifact.

The ContextAssembler should optimize for:

- relevance
- minimal sufficient information
- token efficiency
- explainability

It should not blindly forward all retrieval metadata.

---

## Lifecycle

ReasoningContext is immutable.

Once created, it represents the exact evidence package provided to the reasoning system.

Any modification requires creation of a new context artifact.

This preserves:

- reproducibility
- auditability
- evaluation consistency
- workflow replay capability

---

## Persistence

ReasoningContext is not business data.

It may be checkpointed inside LangGraph state to support:

- HITL interruption
- workflow recovery
- failure investigation
- deterministic replay

It should not be persisted as part of the clinical record.

---

## Architectural Boundary

ReasoningContext represents the final deterministic boundary.

Before ReasoningContext:

- deterministic processing
- retrieval
- ranking
- context assembly

After ReasoningContext:

- probabilistic reasoning
- LLM inference
- agent execution

This separation ensures that AI systems receive bounded evidence rather than uncontrolled application state.