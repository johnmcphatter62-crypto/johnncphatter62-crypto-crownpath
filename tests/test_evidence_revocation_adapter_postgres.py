"""PostgreSQL tests for the trusted revocation transaction adapter."""
from sqlalchemy import select
import pytest

from crownpath.evidence_revocation import EvidenceRevocationDenied
from crownpath.evidence_revocation_adapter import commit_evidence_revocation
from crownpath.models import AssessmentEvidenceRecord, AuditEvent, EvidenceStorageObject, User
from test_evidence_registry_postgres import evidence_db, add_evidence


def test_committed_revocation_persists_with_audit(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"committed-revoke-{suffix}"
    add_evidence(db, ref, learner)
    assert commit_evidence_revocation(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    assert db.scalar(select(AssessmentEvidenceRecord).where(AssessmentEvidenceRecord.evidence_id == ref)).revoked
    assert db.scalar(select(EvidenceStorageObject).where(
        EvidenceStorageObject.storage_reference == f"test-only/{ref}"
    )).revoked
    assert db.scalar(select(AuditEvent).where(AuditEvent.resource_id == ref)).action == "ASSESSMENT_EVIDENCE_REVOKED"
    db.query(AuditEvent).filter(AuditEvent.resource_id == ref).delete()
    db.query(AssessmentEvidenceRecord).filter(AssessmentEvidenceRecord.evidence_id == ref).delete()
    db.query(EvidenceStorageObject).filter(EvidenceStorageObject.storage_reference == f"test-only/{ref}").delete()
    db.query(User).filter(User.user_id.in_([learner, other])).delete(synchronize_session=False)
    db.commit()


def test_denied_revocation_rolls_back_without_audit(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"denied-commit-{suffix}"
    add_evidence(db, ref, learner)
    with pytest.raises(EvidenceRevocationDenied):
        commit_evidence_revocation(db, evidence_id=ref, actor_id=other, actor_role="BARBER")
    assert db.scalars(select(AuditEvent).where(AuditEvent.resource_id == ref)).all() == []
