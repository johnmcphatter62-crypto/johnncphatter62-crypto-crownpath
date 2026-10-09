"""PostgreSQL transaction and authorization tests for evidence revocation."""
from sqlalchemy import select
import pytest

from crownpath.evidence_registry import lookup_verified_evidence_owners
from crownpath.evidence_revocation import EvidenceRevocationDenied, revoke_evidence
from crownpath.models import AssessmentEvidenceRecord, AuditEvent, EvidenceStorageObject
from test_evidence_registry_postgres import evidence_db, add_evidence


def test_owner_revokes_evidence_and_stages_audit(evidence_db):
    db, learner, _, suffix = evidence_db
    ref = f"revoke-{suffix}"
    add_evidence(db, ref, learner, evidence_type="PHOTO", consent=True)
    assert revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER") is True
    db.flush()
    assert db.scalar(select(AssessmentEvidenceRecord).where(AssessmentEvidenceRecord.evidence_id == ref)).revoked
    assert db.scalar(select(EvidenceStorageObject).where(EvidenceStorageObject.storage_reference == f"test-only/{ref}")).revoked
    assert lookup_verified_evidence_owners(db, learner_id=learner, lesson_id="consultation", references=[ref]) == {}
    events = db.scalars(select(AuditEvent).where(AuditEvent.resource_id == ref)).all()
    assert len(events) == 1 and events[0].action == "ASSESSMENT_EVIDENCE_REVOKED"
    assert revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER") is False
    db.flush()
    assert len(db.scalars(select(AuditEvent).where(AuditEvent.resource_id == ref)).all()) == 1


def test_other_learner_cannot_revoke(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"denied-{suffix}"
    add_evidence(db, ref, learner)
    with pytest.raises(EvidenceRevocationDenied):
        revoke_evidence(db, evidence_id=ref, actor_id=other, actor_role="BARBER")
    assert not db.scalar(select(AssessmentEvidenceRecord).where(AssessmentEvidenceRecord.evidence_id == ref)).revoked
    assert db.scalars(select(AuditEvent).where(AuditEvent.resource_id == ref)).all() == []


def test_rollback_restores_evidence_and_audit(evidence_db):
    db, learner, _, suffix = evidence_db
    ref = f"rollback-{suffix}"
    add_evidence(db, ref, learner)
    db.commit()
    try:
        assert revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
        db.flush()
        db.rollback()
        assert not db.scalar(select(AssessmentEvidenceRecord).where(AssessmentEvidenceRecord.evidence_id == ref)).revoked
        assert not db.scalar(select(EvidenceStorageObject).where(EvidenceStorageObject.storage_reference == f"test-only/{ref}")).revoked
        assert db.scalars(select(AuditEvent).where(AuditEvent.resource_id == ref)).all() == []
    finally:
        db.query(AssessmentEvidenceRecord).filter(AssessmentEvidenceRecord.evidence_id == ref).delete()
        db.query(EvidenceStorageObject).filter(EvidenceStorageObject.storage_reference == f"test-only/{ref}").delete()
        db.commit()
