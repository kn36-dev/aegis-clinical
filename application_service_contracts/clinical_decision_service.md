# Application Service Contract — ClinicalDecisionService

## Purpose

`ClinicalDecisionService` owns the business capability of constructing the authoritative clinical decision from physician-reviewed evidence.

Its responsibility is to answer:

> "Given the physician's review of the clinical case, what is the authoritative clinical outcome for this patient encounter?"

The service establishes clinical truth.

It does not persist clinical truth.

It does not perform clinical reasoning.

It does not execute workflow.

Its responsibility is solely to transform physician-reviewed information into an immutable `ClinicalDecision`.

---

# Ownership

## Consumes

### CodingRecommendation

The structured recommendation previously produced by `ClinicalReasoningService`.

Recommendations remain advisory only.

---

### Physician Clinical Decision Submission

A physician-reviewed submission containing the final ICD-11 selections for the patient encounter.

Typical information may include:

- case identifier
- selected ICD-11 codes
- optional review metadata
- optional review notes

The physician is not responsible for computing business classifications.

---

## Creates

### ClinicalDecision

The immutable domain object representing the authoritative clinical truth for the encounter.

Creation flow:

```
CodingRecommendation

+

Physician Submission

        ↓

ClinicalDecisionService

        ↓

ClinicalDecision
```

Only `ClinicalDecisionService` owns construction of the `ClinicalDecision` business object.

---

# Architectural Role

`ClinicalDecisionService` represents the authority boundary of AEGIS.

Everything before this service produces:

- observations
- evidence
- recommendations

Everything after this service preserves:

- institutional truth

The authority progression is:

```
Clinical Observation

↓

Evidence

↓

AI Recommendation

↓

Physician Decision

↓

ClinicalDecision
```

Only the final artifact represents authoritative clinical truth.

---

# Primary Responsibilities

## 1. Clinical Decision Construction

Construct the immutable `ClinicalDecision` object from physician-reviewed information.

The resulting decision represents the official clinical outcome for the encounter.

---

## 2. Recommendation Comparison

Compare physician selections with the original AI recommendations.

This comparison exists to support:

- evaluation
- auditing
- model improvement
- recommendation quality analysis

The original recommendation is preserved for traceability.

---

## 3. Physician Action Classification

Derive deterministic classifications describing how the physician interacted with the recommendation.

Examples include:

- recommendation accepted
- recommendation modified
- recommendation rejected
- additional ICD code added
- suggested ICD code removed

These classifications are computed by the backend rather than submitted by the physician.

---

## 4. Golden Data Preparation

Prepare the physician-approved clinical outcome as canonical institutional knowledge.

The resulting `ClinicalDecision` becomes the authoritative source consumed by downstream persistence services.

---

# Physician Input Boundary

The physician submits clinical conclusions.

The physician does not submit business classifications.

Example:

Submitted:

```
case_id

selected ICD codes

optional notes
```

Derived by the service:

```
accepted

modified

rejected

added

removed
```

Business semantics remain inside the application.

---

# Recommendation Boundary

The service preserves both:

```
CodingRecommendation

↓

ClinicalDecision
```

The recommendation is retained for:

- auditing
- evaluation
- explainability
- future model benchmarking

The recommendation never overrides physician authority.

---

# Clinical Truth Boundary

The resulting `ClinicalDecision` represents:

- physician-approved diagnosis
- authoritative coding outcome
- immutable business truth

The service never treats AI recommendations as truth.

---

# Determinism Classification

`ClinicalDecisionService` is fully deterministic.

Given:

```
Same CodingRecommendation

+

Same Physician Submission

+

Same Business Rules
```

the service must always produce:

```
Same ClinicalDecision
```

This enables:

- deterministic replay
- reproducible auditing
- evaluation consistency
- institutional traceability

---

# Dependencies

Allowed:

```
ClinicalDecision

CodingRecommendation

Business validation

Clinical decision policies
```

---

Not allowed:

```
SQLite

Redis

VectorStore

EmbeddingProvider

LLM

CrewAI

Prompt management

LangGraph

Retrieval infrastructure
```

The service operates purely on business artifacts.

---

# Does Not Own

## Persistence

The service does not:

- write databases
- update Redis
- create audit records
- manage transactions

Persistence belongs to `PersistenceService`.

---

## Clinical Reasoning

The service does not:

- interpret evidence
- call LLMs
- generate recommendations

Those responsibilities belong to `ClinicalReasoningService`.

---

## Workflow

The service does not:

- determine workflow transitions
- manage retries
- invoke infrastructure

Workflow orchestration belongs to LangGraph.

---

## Infrastructure

The service remains independent of:

- database technologies
- cache technologies
- vector databases
- messaging systems

Infrastructure may change without affecting the service contract.

---

# Testing Boundary

`ClinicalDecisionService` must be independently testable.

Tests should verify:

- construction of `ClinicalDecision`
- recommendation comparison
- physician action classification
- deterministic decision generation
- preservation of recommendation traceability

No infrastructure should be required for testing.

---

# Future Replacement Flexibility

The following may change independently:

- AI reasoning implementation
- recommendation structure
- workflow orchestration
- persistence technologies

The stable business capability remains:

```
CodingRecommendation

+

Physician Submission

        ↓

ClinicalDecisionService

        ↓

ClinicalDecision
```

---

# Architectural Philosophy

`ClinicalDecisionService` is the authority boundary of AEGIS.

Artificial intelligence may recommend.

Only physicians decide.

By separating recommendation generation from decision construction, AEGIS ensures that institutional clinical truth is always established through explicit physician authority rather than probabilistic reasoning.

The resulting `ClinicalDecision` becomes the immutable source of truth from which institutional knowledge is preserved and future clinical intelligence may be built.