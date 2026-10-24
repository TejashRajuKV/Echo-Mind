import context_memory as memory
import incremental_verification as iv

def test_claim_family_numeric_change_requires_reverification():
    result = iv.claim_family_similarity(
        "Government announces 15000 rupees for students",
        "Government announces 20000 rupees for students"
    )
    assert result["candidate_family"]
    assert result["material_change"]
    assert result["must_reverify"]

def test_labelled_claim_family_fixture_has_examples():
    result = iv.evaluate_claim_families()
    assert result["n"] >= 20
    assert 0 <= result["precision"] <= 1
    assert 0 <= result["recall"] <= 1

def test_language_detection_has_fallback():
    assert iv.detect_language("ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಸರ್ಕಾರದ ವಿದ್ಯಾರ್ಥಿವೇತನ") == "kn"
