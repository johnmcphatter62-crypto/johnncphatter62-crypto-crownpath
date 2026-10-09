"""PostgreSQL integration tests for trusted evidence ownership and consent.

Only runs against an explicitly configured CI/test PostgreSQL database.
"""
import os
import uuid

import pytest

from crownpath.database import session
from crownpath.evidence_registry import lookup_verified_evidence_owners
from crownpath.models import AssessmentEvidenceRecord, User


@pytest.fixture
def evidence_db():
    url = os.environ.get("CROWNPATH_DATABASE_URL", "")
    if not url.startswith("postgresql") or os.environ.get("CROWNPATH_ENV") != "staging":
        pytest.skip("Requires explicitly configured staging PostgreSQL")
    db = session()
    suffix = uuid.uuid4().hex[:12]
    learner_id = f"ev-learner-{suffix}"
    other_id = f"ev-other-{suffix}"
    db.add_all([
        User(user_id=learner_id, name="Evidence Test Learner", email=f"ev-learner-{suffix}@example.invalid", password_hash="test-only", role="BARBER"),
        User(user_id=other_id, name="Evidence Test Other", email=f"ev-other-{suffix}@example.invalid", password_hash="test-only", role="BARBER"),
    ])
    db.flush()
    try:
        yield db, learner_id, other_id, suffix
    finally:
        db.rollback()
        db.close()


def add_evidence(db, evidence_id, learner_id, lesson_id="consultation", evidence_type="OBSERVATION_NOTE", consent=False, revoked=False):
    db.add(AssessmentEvidenceRecord(
        evidence_id=evidence_id,
        learner_id=learner_id,
        lesson_id=lesson_id,
        evidence_type=evidence_type,
        storage_reference=f"test-only/{evidence_id}",
        consent_confirmed=consent,
        revoked=revoked,
    ))
    db.flush()


def lookup(db, learner_id, refs, lesson="consultation"):
    return lookup_verified_evidence_owners(
        db, learner_id=learner_id, lesson_id=lesson, references=refs,
    )


def test_postgres_accepts_only_matching_learner_and_lesson(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"ev-{suffix}"
    add_evidence(db, ref, learner)
    assert lookup(db, learner, [ref]) == {ref: learner}
    assert lookup(db, other, [ref]) == {}
    assert lookup(db, learner, [ref], lesson="different-lesson") == {}


def test_postgres_rejects_revoked_and_unconsented_media(evidence_db):
    db, learner, _, suffix = evidence_db
    revoked = f"revoked-{suffix}"
    photo = f"photo-{suffix}"
    allowed = f"allowed-{suffix}"
    add_evidence(db, revoked, learner, revoked=True)
    add_evidence(db, photo, learner, evidence_type="PHOTO", consent=False)
    add_evidence(db, allowed, learner, evidence_type="VIDEO", consent=True)
    assert lookup(db, learner, [revoked, photo, allowed]) == {allowed: learner}


def test_postgres_missing_or_duplicate_references_fail_closed(evidence_db):
    db, learner, _, suffix = evidence_db
    ref = f"unique-{suffix}"
    add_evidence(db, ref, learner)
    assert lookup(db, learner, ["missing"]) == {}
    assert lookup(db, learner, [ref, ref]) == {}
