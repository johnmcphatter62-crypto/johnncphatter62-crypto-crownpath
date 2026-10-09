"""PostgreSQL transaction tests for the database-backed evidence storage adapter."""
import os
import uuid

import pytest
from sqlalchemy import select

from crownpath.database import session
from crownpath.database_evidence_storage import DatabaseEvidenceStorage
from crownpath.evidence_storage_adapter import commit_evidence_registration
from crownpath.evidence_storage_verification import EvidenceStorageVerificationDenied
from crownpath.models import AssessmentEvidenceRecord, EvidenceStorageObject, User


@pytest.fixture
def db_records():
    if not os.getenv("CROWNPATH_DATABASE_URL", "").startswith("postgresql") or os.getenv("CROWNPATH_ENV") != "staging":
        pytest.skip("Requires staging PostgreSQL")
    db = session()
    suffix = uuid.uuid4().hex[:12]
    learner_id = f"storage-learner-{suffix}"
    reference = f"storage/{suffix}"
    db.add(User(user_id=learner_id, name="Storage Test", email=f"storage-{suffix}@example.invalid", password_hash="test-only", role="BARBER"))
    db.add(EvidenceStorageObject(
        storage_reference=reference, learner_id=learner_id,
        lesson_id="consultation", evidence_type="PHOTO",
        upload_complete=True, revoked=False,
    ))
    db.flush()
    try:
        yield db, learner_id, reference
    finally:
        db.rollback()
        db.query(AssessmentEvidenceRecord).filter(AssessmentEvidenceRecord.storage_reference == reference).delete(synchronize_session=False)
        db.query(EvidenceStorageObject).filter(EvidenceStorageObject.storage_reference == reference).delete(synchronize_session=False)
        db.query(User).filter(User.user_id == learner_id).delete(synchronize_session=False)
        db.commit()
        db.close()


def arguments(db, learner_id, reference):
    return dict(
        storage=DatabaseEvidenceStorage(db),
        authenticated_learner={"user_id": learner_id, "role": "BARBER", "active": True},
        lesson_id="consultation", evidence_type="PHOTO",
        storage_reference=reference, consent_confirmed=True,
    )


def test_postgres_registration_persists_then_cleanup(db_records):
    db, learner, reference = db_records
    record = commit_evidence_registration(db, **arguments(db, learner, reference))
    assert db.scalar(select(AssessmentEvidenceRecord).where(AssessmentEvidenceRecord.evidence_id == record.evidence_id)) is not None
    db.delete(record)
    db.commit()


def test_postgres_rejects_wrong_lesson_without_evidence_row(db_records):
    db, learner, reference = db_records
    kwargs = arguments(db, learner, reference)
    kwargs["lesson_id"] = "wrong-lesson"
    with pytest.raises(EvidenceStorageVerificationDenied):
        commit_evidence_registration(db, **kwargs)
    assert db.scalar(select(AssessmentEvidenceRecord).where(AssessmentEvidenceRecord.storage_reference == reference)) is None
