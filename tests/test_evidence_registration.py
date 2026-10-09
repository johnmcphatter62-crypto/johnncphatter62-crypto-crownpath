"""Registration policy tests: authenticated learner, media consent and no implicit commit."""
import pytest

from crownpath.evidence_registration import EvidenceRegistrationDenied, stage_evidence_registration


class FakeSession:
    def __init__(self):
        self.added = []
    def add(self, record):
        self.added.append(record)


def registration(**changes):
    data = dict(
        authenticated_learner={"user_id": "learner", "role": "BARBER", "active": True},
        lesson_id="consultation",
        evidence_type="OBSERVATION_NOTE",
        verified_storage_reference="trusted-store/record-1",
    )
    data.update(changes)
    return data


def test_registration_uses_authenticated_learner_and_stages_only():
    db = FakeSession()
    record = stage_evidence_registration(db, **registration())
    assert record.learner_id == "learner"
    assert record.evidence_id.startswith("ev-")
    assert db.added == [record]


@pytest.mark.parametrize("changes", [
    {"authenticated_learner": {"user_id": "learner", "role": "BARBER", "active": False}},
    {"authenticated_learner": {"user_id": "owner", "role": "OWNER", "active": True}},
    {"lesson_id": ""},
    {"evidence_type": "X_RAY"},
    {"verified_storage_reference": ""},
    {"evidence_type": "PHOTO", "consent_confirmed": False},
    {"evidence_type": "VIDEO", "consent_confirmed": False},
    {"consent_confirmed": "yes"},
])
def test_registration_rejects_invalid_metadata(changes):
    db = FakeSession()
    with pytest.raises(EvidenceRegistrationDenied):
        stage_evidence_registration(db, **registration(**changes))
    assert db.added == []


def test_media_with_explicit_consent_can_be_staged():
    db = FakeSession()
    record = stage_evidence_registration(
        db, **registration(evidence_type="PHOTO", consent_confirmed=True)
    )
    assert record.consent_confirmed is True
    assert record.evidence_type == "PHOTO"
