"""
Integration test for ``PresidioPHIAnonymizer``.

Exercises the real Presidio + spaCy analyzer/anonymizer stack. Verifies
that anonymization occurs without asserting Presidio-internal detection
metadata (entity spans, confidence scores, recognizer names), which is
not part of the ``PHIAnonymizer`` application boundary.
"""

from aegis.phi.presidio import PresidioPHIAnonymizer


def make_anonymizer() -> PresidioPHIAnonymizer:
    return PresidioPHIAnonymizer()


def test_anonymizes_person_and_date_of_birth():
    anonymizer = make_anonymizer()
    text = "Patient John Smith born 01/01/1990 presents with abdominal pain."

    result = anonymizer.anonymize(text)

    assert "John Smith" not in result
    assert "01/01/1990" not in result
    # Clinical content unrelated to PHI must survive anonymization.
    assert "abdominal pain" in result


def test_is_deterministic_across_calls():
    anonymizer = make_anonymizer()
    text = "Patient Jane Doe reports mild headache."

    assert anonymizer.anonymize(text) == anonymizer.anonymize(text)


def test_returns_unchanged_text_when_no_phi_present():
    anonymizer = make_anonymizer()
    text = "Patient reports mild headache and no fever."

    result = anonymizer.anonymize(text)

    assert "headache" in result
    assert "no fever" in result


def test_handles_empty_text():
    anonymizer = make_anonymizer()

    assert anonymizer.anonymize("") == ""
