CREATE TABLE IF NOT EXISTS Human_Review_Logs (
    review_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    reviewer_badge_id TEXT NOT NULL,
    action_taken TEXT NOT NULL CHECK (action_taken IN ('APPROVED_ALL', 'OVERRIDDEN_AND_APPROVED', 'REJECTED_CASE')),
    physician_notes TEXT,
    cryptographic_signature TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES patient_case(case_id)
);
