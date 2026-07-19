# Aegis-Clinical Testing & Evaluation

AEGIS distinguishes **software correctness** (deterministic, `tests/`) from
**AI quality evaluation** (`evals/` + `aegis-eval`) — see `CLAUDE.md`'s Testing
Philosophy. This document covers the latter: how retrieval and reasoning
quality are measured today, and where that's headed.

## Current (implemented)

The v1 evaluation framework (`src/aegis/evaluation/`, dataset at
`evals/clinical_cases.jsonl`, CLI: `aegis-eval`) measures two boundaries
independently, reusing the same real application services the production
LangGraph workflow uses — no separate evaluation-only business logic:

**Retrieval evaluation** (`NormalizationService` → `RetrievalService`):
Recall@K, Hit Rate@K, and Mean Reciprocal Rank, computed per case and
averaged across the dataset. Two modes:
- `local` (`config/evaluation.yaml`) — a small, hand-curated ICD-11 fixture
  (`data/eval_icd_fixture.csv`, see its README), no external credentials,
  CI-safe. This is a **regression fixture**, not a representative
  benchmark of retrieval quality against the real taxonomy.
- `production` (`config/evaluation.production.yaml`) — the real Upstash
  Vector index, via the same provider-construction code
  (`aegis.api.bootstrap`) the running application uses.

**Reasoning evaluation** (`ContextAssembler` → `ClinicalReasoningService`):
deterministic scoring only, no LLM-as-judge —
- schema validity (did `ClinicalReasoningService` produce a valid
  `CodingRecommendation` within its own retry budget)
- `expected_code_alignment` — whether the recommended code(s) intersect
  the case's `expected_codes`, `acceptable_codes`, or neither
  (`misaligned`). Deliberately neutral naming: a `misaligned` result means
  the recommendation disagreed with this case's annotation, not that the
  model "hallucinated" — `ClinicalReasoningService` already structurally
  guarantees every recommended code came from real retrieved candidates;
  this axis measures annotation agreement, a separate question.
- evidence grounding — non-empty supporting findings and justification

Every report (`retrieval_report.json`, `reasoning_report.json`,
`summary.md`, written to `.artifacts/evaluations/run_<timestamp>/`) carries
provenance: git commit, dataset hash, config hash, model/provider info, and
retrieval backend, so a result can be reproduced or audited later.

Reasoning evaluation against the real Groq-backed `CrewAIReasoningProvider`
is throttled by a reusable `RateLimiter` (request-based limits enforced
today; token-based budgets are an interface only, not yet enforced — see
`aegis.evaluation.rate_limiter`'s module docstring).

## Why LLM-as-judge is deferred

Reasoning evaluation today scores against fixed, human-authored
`expected_codes`/`acceptable_codes` annotations using set membership and
non-emptiness checks — fully deterministic and reproducible. An
LLM-as-judge layer (a second model scoring the first model's free-text
justification/reasoning_summary) would add real value — richer signal on
justification quality, evidence grounding, and clinical plausibility beyond
code matching — but introduces its own probabilistic-scoring
non-determinism and cost, and needs its own validation before AEGIS trusts
its verdicts. Deferred deliberately, not forgotten.

## Future roadmap

Not implemented today — the items below describe direction, not current
capability. In particular: **Braintrust is not integrated in this codebase
today.** Any mention below is a target, not a claim.

| Evaluation Dimension | Metric Vector | Target Threshold | Planned Verification Protocol |
| :--- | :--- | :--- | :--- |
| **Clinical Taxonomy Accuracy** | Extraction Precision & Recall ($F_1$ Score) | $F_1 \ge 0.94$ | Braintrust-tracked continuous evaluation across an expanded synthetic validation dataset (today: 8 hand-authored cases in `evals/clinical_cases.jsonl`). |
| **Reasoning Quality (qualitative)** | LLM-as-judge score on justification/evidence quality | TBD | A second model scores `reasoning_summary`/`justification` text quality, layered on top of (not replacing) today's deterministic code-alignment scoring. |
| **Physician Correction Rate** | Human-in-the-loop override rate | TBD | Track how often physician review (`ClinicalDecisionService`) overrides the AI recommendation, once enough real HITL review volume exists to make the rate meaningful. |
| **System Cache Efficiency** | Financial Token Reduction Curve | $\ge 75\%$ Cost Elimination | Telemetry span metrics comparing raw ingress tokens against cache write-backs (depends on `docs/observability.md`'s OpenTelemetry instrumentation, not yet wired up). |
| **State Chart Determinism** | Path Invariance Under Adversarial Loads | $100\%$ Compliant Routing | Randomized-exception injection across parallel test graph runs. |
| **Schema Integrity** | Boundary Rejection Resilience | $100\%$ Catchment Rate | Property-based data fuzzing against input schemas. |
| **HITL Persistence Stability** | Thread Recovery Fidelity | $100\%$ Hydration Success | Forced restarts while execution threads are suspended. |
