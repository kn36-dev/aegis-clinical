CREATE TABLE IF NOT EXISTS clinical_trial (
    trial_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4')),
    sponsor TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Recruiting', 'Completed', 'Suspended')),
    raw_eligibility_criteria TEXT NOT NULL
);

-- A trial is always unique, so primary key
-- Title: human-readable semantic label
-- Sponsor: Compliance Segmentation, Institutional Reporting, Downstream Analytics 
-- (which pharma sponsors dominate which ICD clusters)
-- raw_eligibility_criteria: LLM semantic parser, embedding, rule extraction
-- Phase: commonly represent things like:
-- Phase 1 → healthy volunteers, high safety margin
-- Phase 2 → small patient groups, early efficacy
-- Phase 3 → large population, stricter inclusion criteria
-- Phase 4 → post-market real-world patients

-- Normally the embedding is title + eligibility_criteria + phase metadata