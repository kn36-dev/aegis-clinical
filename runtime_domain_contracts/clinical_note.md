# Runtime Domain Contract — ClinicalNote

## Purpose

`ClinicalNote` is the immutable representation of a physician-authored clinical observation for a single patient encounter. It serves as the canonical entry point into the AEGIS runtime pipeline and represents the original clinical truth from which all downstream deterministic artifacts and AI-assisted reasoning are derived.

The `ClinicalNote` itself contains no interpretation, diagnosis, workflow state, or AI-generated information. Its responsibility is solely to represent the existence of a clinical observation and provide stable identity throughout the lifetime of the case.

---

## Ownership

**Created by**

- Application ingress after request validation.

**Consumed by**

- Retrieval subsystem
- Workflow orchestration
- Audit services
- Persistence layer

The `ClinicalNote` should never be created by downstream workflow components.

---

## Lifetime

The object is immutable and long-lived.

It is persisted as part of the application's system of record and remains stable throughout the entire lifecycle of the clinical case. LangGraph checkpointing may reference the same `ClinicalNote` across multiple workflow resumptions without modifying the object itself.

---

## Required Information

The contract should contain only the minimum information required to uniquely identify and retrieve the original clinical observation.

Typical fields include:

- `case_id`
  - Unique identifier for a single patient encounter.
  - One encounter corresponds to exactly one `ClinicalNote`.

- `patient_id`
  - Reference to the patient identity.
  - Personal identifying information is assumed to reside in an external secured identity system.

- `content_reference`
  - Repository reference used to retrieve the encrypted clinical note contents.
  - The domain owns the reference rather than the storage implementation.

---

## Explicit Boundaries

`ClinicalNote` intentionally does **not** contain:

- ICD-11 classifications
- AI-generated recommendations
- physician decisions
- workflow state
- retrieval results
- embeddings
- normalized text
- anonymized text
- hashes
- confidence scores

Those are produced later by deterministic processing or probabilistic reasoning.

---

## Architectural Role

`ClinicalNote` represents the immutable source of truth for a clinical observation.

Every downstream artifact—including normalization, retrieval, reasoning, and physician-approved coding decisions—must remain traceable back to the originating `ClinicalNote`.

The object itself never changes; only new immutable artifacts are derived from it.