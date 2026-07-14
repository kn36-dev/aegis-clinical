# Runtime Domain Contract — CodingRecommendation

## Purpose

`CodingRecommendation` represents the structured recommendation produced by the AI reasoning subsystem after evaluating a clinical note against the semantically retrieved ICD taxonomy candidates.

It is **not** a clinical fact.

It is an AI-generated recommendation intended to support physician decision making.

This contract forms the boundary between probabilistic reasoning and human review.

---

# Responsibilities

The CodingRecommendation is responsible for:

- representing AI-generated ICD coding recommendations
- preserving structured clinical justification
- linking recommendations back to retrieved candidates
- providing explainable evidence for physician review
- exposing deterministic, strongly typed outputs for downstream workflow

The CodingRecommendation is **not** responsible for:

- performing retrieval
- selecting retrieval candidates
- validating against the ICD taxonomy
- making the final clinical decision
- persisting approved ICD codes

---

# Lifecycle

Created by:

- AI Reasoning Service (CrewAI/PydanticAI boundary)

Consumed by:

- Human Review (HITL)
- LangGraph workflow
- Evaluation framework
- Replay tooling

Never directly persisted as clinical truth.

May be checkpointed for workflow replay and audit purposes.

---

# Invariants

A CodingRecommendation must:

- reference an existing RetrievalResult
- only recommend ICD concepts originating from RetrievalResult
- contain structured recommendations
- remain immutable after creation

A CodingRecommendation must never:

- invent ICD codes outside RetrievalResult
- mutate RetrievalResult
- bypass physician approval
- become the source of truth

---

# Recommendation Structure

Each recommendation should contain:

- RetrievalCandidate reference
- ICD code
- supported clinical findings
- conflicting clinical findings
- structured justification
- reasoning summary

Evidence should be represented as structured observations rather than free-form narrative whenever possible.

---

# Boundaries

Inputs:

- ReasoningContext

Outputs:

- ClinicalDecision (after physician review)

---

# Architectural Role

CodingRecommendation is the final probabilistic artifact produced by the AI reasoning pipeline.

It provides explainable, structured recommendations for human validation while remaining completely separated from authoritative clinical truth.

Only after physician approval may recommendations be transformed into ClinicalDecision objects.