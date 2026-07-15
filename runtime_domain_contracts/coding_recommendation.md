# Runtime Domain Contract — CodingRecommendation

## Purpose

`CodingRecommendation` represents the structured recommendation produced by the AI reasoning subsystem after evaluating a clinical note against the semantically retrieved ICD taxonomy candidates.

It is **not** a clinical fact.

It is an AI-generated recommendation intended to support physician decision making.

This contract forms the boundary between probabilistic reasoning and human review.

---

# Architectural Boundary

CodingRecommendation is produced from a ReasoningContext, never directly from
a RetrievalResult:

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

`RetrievalService` owns retrieval and produces `RetrievalResult`.
`ContextAssembler` owns curating that result into the bounded
`ReasoningContext` handed across the reasoning boundary. By the time
`ClinicalReasoningService` runs, `RetrievalResult` and `RetrievalCandidate`
are no longer available — only `ReasoningContext` and its `CandidateConcept`
candidates are. Every reference this contract makes to "retrieved evidence"
therefore means the ICD-11 codes present in `ReasoningContext.candidates`,
not `RetrievalResult` itself.

---

# Responsibilities

The CodingRecommendation is responsible for:

- representing AI-generated ICD coding recommendations
- preserving structured clinical justification
- linking recommendations back to the ReasoningContext candidates that were reasoned over, via EvidenceReference
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

CodingRecommendation is produced from a ReasoningContext, not directly from a
RetrievalResult — see Architectural Boundary below. Its referential
invariants are therefore expressed against ReasoningContext.

A CodingRecommendation must:

- reference the ReasoningContext it was reasoned over, via an
  EvidenceReference (see Evidence Reference) rather than by embedding
  ReasoningContext, RetrievalResult, or RetrievalCandidate/CandidateConcept
  objects
- only recommend ICD-11 codes present in the ReasoningContext.candidates it
  was reasoned over
- contain structured recommendations
- remain immutable after creation

A CodingRecommendation must never:

- invent ICD codes outside the ReasoningContext it was reasoned over
- mutate the ReasoningContext it was reasoned over
- bypass physician approval
- become the source of truth

---

# Recommendation Structure

Each recommendation should contain:

- ICD code
- supported clinical findings
- conflicting clinical findings
- structured justification
- reasoning summary

Evidence should be represented as structured observations rather than free-form narrative whenever possible.

---

# Evidence Reference

CodingRecommendation as a whole (not each recommendation individually) carries
an `EvidenceReference` — a lightweight, identifier-only pointer to the bounded
evidence it was reasoned over.

It exists to answer "why was this recommended, and out of what alternatives?"
without CodingRecommendation embedding ReasoningContext, RetrievalResult, or
RetrievalCandidate/CandidateConcept objects. Concretely, it carries the ICD-11
codes present in the ReasoningContext's candidate set at the time of
reasoning — a superset of, or equal to, the codes actually recommended.

`case_id` (already a top-level CodingRecommendation field) identifies which
clinical case produced the recommendation; `EvidenceReference` identifies
which candidate evidence that reasoning pass had available. Together they
give an auditor enough to trace a recommendation back to a specific case and
evidence set, and — because retrieval and context assembly are deterministic
— to deterministically reproduce the originating ReasoningContext for
comparison, without CodingRecommendation needing to store or reference the
ReasoningContext object itself.

---

# Boundaries

Inputs:

- ReasoningContext (never RetrievalResult or RetrievalCandidate directly —
  see Architectural Boundary)

Outputs:

- ClinicalDecision (after physician review)

---

# Architectural Role

CodingRecommendation is the final probabilistic artifact produced by the AI reasoning pipeline.

It provides explainable, structured recommendations for human validation while remaining completely separated from authoritative clinical truth.

Only after physician approval may recommendations be transformed into ClinicalDecision objects.