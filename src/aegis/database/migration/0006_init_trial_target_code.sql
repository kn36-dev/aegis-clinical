CREATE TABLE IF NOT EXISTS trial_target_code (
    trial_id TEXT NOT NULL,
    icd11_code TEXT NOT NULL,
    criterion_type TEXT NOT NULL CHECK (criterion_type IN ('INCLUSION', 'EXCLUSION')),
    PRIMARY KEY (trial_id, icd11_code),
    FOREIGN KEY (trial_id) REFERENCES clinical_trial(trial_id) ON DELETE CASCADE,
    FOREIGN KEY (icd11_code) REFERENCES icd11_taxonomy_reference(code)
);

-- EXPLANATION:

-- For each patient:

-- Required Trial Codes
--     minus
-- Patient Codes

-- must be empty

-- AND

-- Excluded Trial Codes
--     intersect
-- Patient Codes

-- must be empty.

-- WITH patient_icd_profile AS (
--     SELECT DISTINCT
--         pc.patient_id,
--         pec.icd11_code
--     FROM patient_case pc
--     JOIN patient_extracted_code pec
--         ON pc.case_id = pec.case_id
-- )

-- SELECT DISTINCT p.patient_id
-- FROM patient_icd_profile p
-- WHERE

--     NOT EXISTS (
--         SELECT t.icd11_code
--         FROM trial_target_code t
--         WHERE t.trial_id = 'NCT001'
--           AND t.criterion_type = 'INCLUSION'

--         EXCEPT

--         SELECT p2.icd11_code
--         FROM patient_icd_profile p2
--         WHERE p2.patient_id = p.patient_id
--     )

--     AND

--     NOT EXISTS (
--         SELECT t.icd11_code
--         FROM trial_target_code t
--         WHERE t.trial_id = 'NCT001'
--           AND t.criterion_type = 'EXCLUSION'

--         INTERSECT

--         SELECT p2.icd11_code
--         FROM patient_icd_profile p2
--         WHERE p2.patient_id = p.patient_id
--     );