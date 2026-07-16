-- ============================================================================
-- 0010: patient_case.content_reference - link case to its content record
-- ============================================================================
--
-- ClinicalNote.content_reference is a direct, 1:1-owned attribute of the
-- case (ClinicalNoteService creates exactly one ClinicalNote per case_id).
-- Nullable because content may be written to clinical_note_content before
-- or independently of the patient_case row being created.

ALTER TABLE patient_case ADD COLUMN content_reference TEXT;
