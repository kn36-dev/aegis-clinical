# `eval_icd_fixture.csv`

## Source

Rows extracted verbatim (same column schema, unmodified values) from
`data/only_medical_symptoms.csv` — the curated WHO ICD-11 export the real
offline indexing pipeline seeds into `icd11_taxonomy`
(`make db-seed-icd` / `aegis-db seed --icd`).

## Extraction date

2026-07-19.

## Selection

25 rows: the exact ICD-11 codes referenced by `evals/clinical_cases.jsonl`'s
`expected_codes`/`acceptable_codes`, plus realistic distractors from the same
or adjacent chapters (parent/child pairs, semantically nearby symptom codes)
so ranking has something non-trivial to discriminate.

## Purpose and scope — read before reusing this file

This fixture exists **only** to give `aegis-eval retrieval`'s deterministic
local mode (`retrieval.mode: local` in `config/evaluation.yaml`) a small,
fixed, reproducible index that requires no external credentials and runs
fast in CI. It is a **regression fixture**, not a sample of, or substitute
for, the real ~15k-row production ICD-11 taxonomy.

**It is not a representative ICD-11 retrieval benchmark.** Recall@K /
Hit Rate@K / MRR computed against it say only "did retrieval behavior
regress against this fixed 25-row index", not "how good is retrieval
against the real taxonomy". For that, run `aegis-eval` with
`config/evaluation.production.yaml` against the real Upstash Vector index.
