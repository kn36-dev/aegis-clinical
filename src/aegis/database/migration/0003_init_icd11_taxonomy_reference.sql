DROP TABLE IF EXISTS icd11_taxonomy;

CREATE TABLE icd11_taxonomy (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    class_kind TEXT NOT NULL,
    context_path TEXT,
    chapter_no TEXT,
    is_leaf INTEGER,
    is_residual INTEGER
);


-- CREATE TABLE IF NOT EXISTS icd11_taxonomy_reference (
--     code TEXT PRIMARY KEY,
--     title TEXT NOT NULL,
--     class_kind TEXT NOT NULL,
--     context_path TEXT NOT NULL
-- );

-- Example value
-- Code:         1A03.Z
-- Title:        Intestinal infections due to Escherichia coli, unspecified
-- Class Kind:   category
-- Context Path: Gastroenteritis or colitis of infectious origin > Bacterial intestinal infections > Intestinal infections due to Escherichia coli > Intestinal infections due to Escherichia coli, unspecified