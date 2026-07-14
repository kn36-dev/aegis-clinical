# Runtime Domain Contract — ClinicalDecision

## Purpose

`ClinicalDecision` represents the only authoritative clinical truth produced within the AEGIS runtime.

It captures the physician-approved ICD-11 classifications for a clinical case after reviewing AI-generated recommendations.

Unlike `CodingRecommendation`, which represents probabilistic AI assistance, `ClinicalDecision` represents deterministic human-approved clinical knowledge.

This contract defines the boundary where:

```
AI-assisted reasoning

↓

Physician validation

↓

Trusted clinical truth
```

occurs.

Once created, `ClinicalDecision` becomes the authoritative source from which durable persistence, evaluation datasets, analytical projections, and future institutional learning are derived.

---

# Responsibilities

`ClinicalDecision` is responsible for:

- Representing physician-approved ICD-11 classifications.
- Recording the relationship between AI recommendations and final physician decisions.
- Preserving immutable clinical truth after human validation.
- Maintaining traceability back to the originating clinical observation and deterministic preprocessing artifacts.
- Serving as the golden reference dataset for evaluation and future system improvement.

`ClinicalDecision` is **not responsible for**:

- AI reasoning.
- Retrieval.
- Similarity scoring.
- Prompt execution.
- Candidate generation.
- Clinical interpretation.
- Persistence execution.
- Cache updates.
- Workflow transitions.

Those responsibilities belong to other application layers.

---

# Ownership

## Created by

`ClinicalDecisionService`

after receiving:

```
CodingRecommendation

+

Physician Decision Submission

↓

ClinicalDecision
```

The physician provides the final clinical decision.

The application constructs the immutable domain artifact.

---

## Consumed by

- PersistenceService
- Audit systems
- Evaluation pipelines
- Analytics systems
- Future institutional knowledge systems

---

# Lifecycle

`ClinicalDecision` is created only after physician review.

The physician submits approved ICD-11 classifications through the application interface.

Before construction, the backend validates:

- referenced clinical case existence,
- ICD-11 code validity,
- workflow consistency,
- submission integrity.

Once created:

```
ClinicalDecision
```

is immutable.

Corrections are represented as new decisions rather than mutations.

This preserves:

- audit history,
- reproducibility,
- institutional learning.

---

# Required Information

A `ClinicalDecision` contains:

## Identity

### decision_id

Unique identifier for this clinical decision event.

---

### case_id

Reference to the clinical encounter associated with this decision.

---

### patient_id_reference

Reference to the patient identity boundary.

The contract does not contain raw patient identity information.

---

# Clinical Outcome

## approved_icd_codes

The final ICD-11 classifications approved by the physician.

A single clinical encounter may contain multiple approved classifications.

---

# Recommendation Traceability

`ClinicalDecision` preserves the relationship between:

```
CodingRecommendation

↓

Physician Decision
```

For each ICD-11 candidate, the decision records whether it was:

- Accepted from AI recommendation.
- Added manually by physician.
- Removed from AI recommendation.
- Modified during physician review.

This allows evaluation of:

- AI agreement rate.
- False recommendations.
- Missing suggestions.
- Physician correction patterns.

---

# Normalization Traceability

`ClinicalDecision` contains a reference to the deterministic preprocessing artifact that produced the evidence used during reasoning.

Example:

```
normalized_note_id
```

This reference allows downstream systems to trace:

```
ClinicalDecision

↓

NormalizedClinicalNote

↓

Original ClinicalNote
```

without embedding:

- raw clinical text,
- normalized content,
- cache keys,
- infrastructure identifiers.

The contract stores traceability, not implementation details.

---

# Authority Boundary

`ClinicalDecision` represents the transition from recommendation to truth.

The authority hierarchy is:

```
ClinicalNote

↓

NormalizedClinicalNote

↓

RetrievalResult

↓

ReasoningContext

↓

CodingRecommendation

↓

ClinicalDecision
```

Only the final artifact represents authoritative clinical knowledge.

No intermediate AI-generated artifact may directly create durable clinical truth.

---

# Persistence Boundary

`ClinicalDecision` does not perform persistence.

It does not know:

- SQLite.
- Redis.
- repositories.
- storage projections.
- transactions.

Instead:

```
ClinicalDecision

↓

PersistenceService

↓

Durable storage

+

Derived projections
```

Persistence technologies may change without affecting the domain contract.

---

# Determinism

`ClinicalDecision` is deterministic.

Given:

```
Same CodingRecommendation

+

Same Physician Submission

+

Same Business Rules
```

the resulting:

```
ClinicalDecision
```

must remain identical.

This enables:

- deterministic replay.
- auditing.
- evaluation consistency.
- institutional traceability.

---

# Design Principles

`ClinicalDecision` embodies the core philosophy of AEGIS:

- Human judgment is the final authority.
- AI recommendations remain advisory.
- Durable truth begins only after physician approval.
- Historical decisions are preserved rather than overwritten.
- Every downstream projection originates from physician-approved truth.
- Infrastructure details remain outside business concepts.

`ClinicalDecision` therefore represents the immutable boundary between AI assistance and trusted clinical knowledge.