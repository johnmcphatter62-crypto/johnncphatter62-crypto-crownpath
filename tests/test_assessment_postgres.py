"""PostgreSQL-backed practical assessment transaction tests.

Runs against CrownPath CI's disposable PostgreSQL database. Uses only test
records and rolls back committed rows in teardown; never touches production.
"""
import os
import uuid

import pytest
from sqlalchemy import select

from crownpath.database import session
from crownpath.models import AuditEvent, PracticalAssessment, User
from crownpath.assessment_repository import stage_assessment_review


@pytest.fixture
def assessment_db():
    if not os.environ.get("CROWNPATH_DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("PostgreSQL integration test requires explicit test database URL")
    db = session()
    suffix = uuid.uuid4().hex[:12]
    learner_id = f"test-learner-{suffix}"
    reviewer_id = f"test-reviewer-{suffix}"
    db.add_all([
        User(user_id=learner_id, name="Assessment Test Learner", email=f"learner-{suffix}@example.invalid", password_hash="test-only", role="BARBER"),
        User(user_id=reviewer_id, name="Assessment Test Reviewer", email=f"reviewer-{suffix}@example.invalid", password_hash="test-only", role="INSTRUCTOR"),
    ])
    db.commit()
    try:
        yield db, learner_id, reviewer_id
    finally:
        db.rollback()
        db.query(AuditEvent).filter(AuditEvent.resource_type == "PRACTICAL_ASSESSMENT", AuditEvent.user_id == reviewer_id).delete(synchronize_session=False)
        db.query(PracticalAssessment).filter(PracticalAssessment.reviewer_id == reviewer_id).delete(synchronize_session=False)
        db.query(User).filter(User.user_id.in_([learner_id, reviewer_id])).delete(synchronize_session=False)
        db.commit()
        db.close()


def stage(db, learner_id, reviewer_id):
    return stage_assessment_review(
        db,
        learner_id=learner_id,
        reviewer_id=reviewer_id,
        lesson_id="consultation",
        rubric_version="v1",
        knowledge_percent=80,
        competency_scores={"consultation": 3},
        safety_gates={"sanitation": True},
        evidence_refs=["CP-EV-TEST"],
        decision="APPROVED",
    )


def test_postgres_commits_assessment_and_audit_together(assessment_db):
    db, learner_id, reviewer_id = assessment_db
    record = stage(db, learner_id, reviewer_id)
    db.commit()
    assert db.get(PracticalAssessment, record.assessment_id) is not None
    audit = db.scalar(select(AuditEvent).where(AuditEvent.resource_id == record.assessment_id))
    assert audit is not None
    assert audit.result == "APPROVED"


def test_postgres_rollback_discards_both_staged_records(assessment_db):
    db, learner_id, reviewer_id = assessment_db
    record = stage(db, learner_id, reviewer_id)
    db.flush()
    db.rollback()
    assert db.get(PracticalAssessment, record.assessment_id) is None
    audit = db.scalar(select(AuditEvent).where(AuditEvent.resource_id == record.assessment_id))
    assert audit is None
