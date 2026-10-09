"""Trusted storage verification policy regression tests."""
import pytest

from crownpath.evidence_storage_verification import (
    EvidenceStorageVerificationDenied,
    verify_storage_metadata,
)


def valid():
    return {
        "learner_id": "learner",
        "lesson_id": "consultation",
        "evidence_type": "PHOTO",
        "storage_reference": "secure/object-1",
        "upload_complete": True,
        "revoked": False,
    }


def check(metadata):
    return verify_storage_metadata(
        learner_id="learner", lesson_id="consultation",
        evidence_type="PHOTO", storage_reference="secure/object-1",
        trusted_metadata=metadata,
    )


def test_matching_completed_storage_metadata_passes():
    assert check(valid()) == "secure/object-1"


@pytest.mark.parametrize("field,value", [
    ("learner_id", "other"),
    ("lesson_id", "another-lesson"),
    ("evidence_type", "DOCUMENT"),
    ("storage_reference", "secure/other-object"),
    ("upload_complete", False),
    ("revoked", True),
])
def test_storage_mismatches_fail_closed(field, value):
    metadata = valid()
    metadata[field] = value
    with pytest.raises(EvidenceStorageVerificationDenied):
        check(metadata)


def test_missing_trusted_metadata_is_rejected():
    with pytest.raises(EvidenceStorageVerificationDenied):
        check(None)
