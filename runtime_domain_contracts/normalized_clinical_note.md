# Runtime Domain Contract — NormalizedClinicalNote

## Purpose

`NormalizedClinicalNote` represents the canonical deterministic representation of an anonymized clinical note. Its purpose is to provide a stable, reproducible, and semantically equivalent clinical narrative that can be safely consumed by downstream deterministic and probabilistic components without exposing protected health information (PHI).

Unlike the original `ClinicalNote`, this artifact is intended for runtime processing. It preserves the clinical meaning of the physician's documentation while removing formatting inconsistencies and applying deterministic normalization rules. It serves as the canonical textual representation from which semantic retrieval and downstream AI reasoning operate.

---

## Ownership

**Created by**

- Deterministic preprocessing pipeline immediately after anonymization.

**Consumed by**

- Embedding provider
- Retrieval subsystem
- Context assembly
- CrewAI orchestration
- Evaluation pipeline

The `NormalizedClinicalNote` is the canonical textual representation used throughout the AI processing pipeline.

---

## Lifetime

The object is immutable and ephemeral.

It exists as a deterministic processing artifact and may be checkpointed by the workflow engine to avoid unnecessary recomputation during workflow resumption. It is not considered part of the application's long-term business record.

---

## Required Information

Typical fields include:

- `clinical_note`
  - Reference to the originating immutable `ClinicalNote`.

- `normalized_text`
  - Canonical anonymized clinical narrative preserving the original clinical meaning.

- `normalization_version`
  - Version identifier describing the deterministic normalization algorithm used to generate the artifact.

---

## Explicit Boundaries

`NormalizedClinicalNote` intentionally does **not** contain:

- cache hashes
- Redis keys
- embeddings
- vector identifiers
- retrieval candidates
- workflow state
- ICD classifications
- AI-generated reasoning
- physician decisions

Cache-specific canonicalization remains a separate downstream responsibility.

---

## Architectural Role

`NormalizedClinicalNote` establishes the canonical textual representation used throughout the runtime AI pipeline.

Every downstream semantic operation—including embedding generation, vector retrieval, context assembly, evaluation, and AI reasoning—should operate exclusively on this artifact. By separating semantic normalization from cache optimization, the architecture preserves clinical meaning while allowing deterministic cache strategies to evolve independently.