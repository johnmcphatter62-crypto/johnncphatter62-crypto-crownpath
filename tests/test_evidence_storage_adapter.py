"""Trusted storage adapter and registration transaction tests."""
from unittest.mock import Mock

import pytest

from crownpath.evidence_storage_adapter import commit_evidence_registration
from crownpath.evidence_storage_verification import EvidenceStorageVerificationDenied


class FakeDB:
    def __init__(self, fail_commit=False):
        self.records = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = fail_commit

    def add(self, record):
        self.records.append(record)

    def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("database unavailable")

    def rollback(self):
        self.rollbacks += 1
        self.records.clear()


def arguments(storage):
    return dict(
        storage=storage,
        authenticated_learner={"user_id": "learner", "role": "BARBER", "active": True},
        lesson_id="consultation",
        evidence_type="PHOTO",
        storage_reference="private/object-1",
        consent_confirmed=True,
    )


def verified_metadata(**changes):
    metadata = {
        "learner_id": "learner",
        "lesson_id": "consultation",
        "evidence_type": "PHOTO",
        "storage_reference": "private/object-1",
        "upload_complete": True,
        "revoked": False,
    }
    metadata.update(changes)
    return metadata


def test_verified_storage_commits_registration():
    storage = Mock()
    storage.get_verified_metadata.return_value = verified_metadata()
    db = FakeDB()
    record = commit_evidence_registration(db, **arguments(storage))
    storage.get_verified_metadata.assert_called_once_with("private/object-1")
    assert record.learner_id == "learner"
    assert db.commits == 1
    assert db.rollbacks == 0


@pytest.mark.parametrize("metadata", [
    None,
    verified_metadata(learner_id="different"),
    verified_metadata(lesson_id="different"),
    verified_metadata(upload_complete=False),
    verified_metadata(revoked=True),
])
def test_invalid_storage_rolls_back_without_commit(metadata):
    storage = Mock()
    storage.get_verified_metadata.return_value = metadata
    db = FakeDB()
    with pytest.raises(EvidenceStorageVerificationDenied):
        commit_evidence_registration(db, **arguments(storage))
    assert db.commits == 0
    assert db.rollbacks == 1
    assert db.records == []


def test_database_commit_failure_rolls_back():
    storage = Mock()
    storage.get_verified_metadata.return_value = verified_metadata()
    db = FakeDB(fail_commit=True)
    with pytest.raises(RuntimeError, match="database unavailable"):
        commit_evidence_registration(db, **arguments(storage))
    assert db.commits == 1
    assert db.rollbacks == 1
    assert db.records == []
