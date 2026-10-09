"""Tests for assessment evidence metadata validation."""
import pytest

from crownpath.assessment_evidence import validate_assessment_evidence


def evidence(**changes):
    value = {"type": "OBSERVATION_NOTE", "reference": "CP-EV-123", "observation_note": "Observed safe consultation."}
    value.update(changes)
    return value


def test_valid_observation_note():
    assert validate_assessment_evidence(evidence()).valid


def test_explicit_consent_for_photo():
    photo = evidence(type="PHOTO", consent_confirmed=False)
    assert not validate_assessment_evidence(photo, require_consent=True).valid
    photo["consent_confirmed"] = True
    assert validate_assessment_evidence(photo, require_consent=True).valid


@pytest.mark.parametrize("changes", [
    {"type": "UNKNOWN"},
    {"reference": ""},
    {"reference": "bad\nref"},
    {"observation_note": ""},
    {"observation_note": "x" * 4001},
])
def test_invalid_evidence_is_rejected(changes):
    assert not validate_assessment_evidence(evidence(**changes)).valid


def test_non_mapping_is_rejected():
    assert not validate_assessment_evidence(None).valid


def test_consent_requires_boolean_true():
    assert not validate_assessment_evidence(evidence(consent_confirmed="yes"), require_consent=True).valid
