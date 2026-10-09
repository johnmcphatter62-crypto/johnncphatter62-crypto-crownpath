"""PostgreSQL authorization tests for scoped evidence audit lookup."""
from sqlalchemy import select
import pytest

from crownpath.evidence_audit import EvidenceAuditAccessDenied, list_evidence_revocation_audit
from crownpath.evidence_revocation import revoke_evidence
from crownpath.models import AuditEvent, User
from test_evidence_registry_postgres import evidence_db, add_evidence


def test_owner_can_read_only_own_revocation_audit(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"audit-owner-{suffix}"
    add_evidence(db, ref, learner)
    revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    db.flush()
    events = list_evidence_revocation_audit(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    assert len(events) == 1
    assert events[0].user_id == learner
    assert events[0].action == "ASSESSMENT_EVIDENCE_REVOKED"
    with pytest.raises(EvidenceAuditAccessDenied):
        list_evidence_revocation_audit(db, evidence_id=ref, actor_id=other, actor_role="BARBER")


def test_forged_admin_and_inactive_user_cannot_read_audit(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"audit-guard-{suffix}"
    add_evidence(db, ref, learner)
    with pytest.raises(EvidenceAuditAccessDenied):
        list_evidence_revocation_audit(db, evidence_id=ref, actor_id=other, actor_role="ADMIN")
    db.get(User, learner).active = False
    db.flush()
    with pytest.raises(EvidenceAuditAccessDenied):
        list_evidence_revocation_audit(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")


def test_verified_admin_can_read_scoped_audit(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"audit-admin-{suffix}"
    add_evidence(db, ref, learner)
    revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    db.get(User, other).role = "ADMIN"
    db.flush()
    events = list_evidence_revocation_audit(db, evidence_id=ref, actor_id=other, actor_role="ADMIN")
    assert len(events) == 1
    assert events[0].resource_id == ref
