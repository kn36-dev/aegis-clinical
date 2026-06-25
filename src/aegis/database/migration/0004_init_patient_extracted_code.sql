CREATE TABLE IF NOT EXISTS patient_extracted_code (
    case_id TEXT NOT NULL,
    icd11_code TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    -- Source could be crewAI, LLM, or Physician
    -- Could be improved by an enum
    extraction_source TEXT NOT NULL,
    PRIMARY KEY (case_id, icd11_code),
    FOREIGN KEY (case_id) REFERENCES patient_case(case_id) ON DELETE CASCADE,
    FOREIGN KEY (icd11_code) REFERENCES icd11_taxonomy_reference(code)
);
 
-- Remember, here 1 icd11_code translates to 1 row
-- So 1 case_id can have multiple rows (1 medical case could diagnose multiple diseases)