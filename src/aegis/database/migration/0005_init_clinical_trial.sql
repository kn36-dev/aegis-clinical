CREATE TABLE IF NOT EXISTS Clinical_trial (
    trial_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4')),
    sponsor TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Recruiting', 'Completed', 'Suspended')),
    raw_eligibility_criteria TEXT NOT NULL
);
