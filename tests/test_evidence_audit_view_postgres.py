"""PostgreSQL privacy tests for the revocation audit projection."""
import pytest

from crownpath.evidence_audit import EvidenceAuditAccessDenied
from crownpath.evidence_audit_view import evidence_revocation_history
from crownpath.evidence_revocation import revoke_evidence
from test_evidence_registry_postgres import evidence_db, add_evidence


def test_owner_sees_only_allowlisted_audit_fields(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"privacy-audit-{suffix}"
    add_evidence(db, ref, learner)
    revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    db.flush()
    history = evidence_revocation_history(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    assert len(history) == 1
    assert set(history[0]) == {"action", "result", "occurred_at"}
    assert history[0]["action"] == "ASSESSMENT_EVIDENCE_REVOKED"
    assert "storage_reference" not in history[0]
    assert "user_id" not in history[0]
    with pytest.raises(EvidenceAuditAccessDenied):
        evidence_revocation_history(db, evidence_id=ref, actor_id=other, actor_role="BARBER")


@pytest.mark.parametrize("limit", [0, -1, 101, True, 1.5, "10"])
def test_invalid_audit_history_limits_fail_closed(evidence_db, limit):
    db, learner, _, suffix = evidence_db
    ref = f"privacy-limit-{suffix}"
    add_evidence(db, ref, learner)
    with pytest.raises(ValueError):
        evidence_revocation_history(db, evidence_id=ref, actor_id=learner, actor_role="BARBER", limit=limit)


def test_empty_audit_history_for_unrevoked_evidence(evidence_db):
    db, learner, _, suffix = evidence_db
    ref = f"privacy-empty-{suffix}"
    add_evidence(db, ref, learner)
    assert evidence_revocation_history(db, evidence_id=ref, actor_id=learner, actor_role="BARBER") == []


def test_history_limit_applies_to_database_results(evidence_db):
    from crownpath.models import AuditEvent

    db, learner, _, suffix = evidence_db
    ref = f"privacy-bounded-{suffix}"
    add_evidence(db, ref, learner)
    for index in range(5):
        db.add(AuditEvent(
            user_id=learner,
            action="ASSESSMENT_EVIDENCE_REVOKED",
            category="ASSESSMENT",
            resource_type="EVIDENCE",
            resource_id=ref,
            result="SUCCESS",
        ))
        db.flush()
    history = evidence_revocation_history(
        db, evidence_id=ref, actor_id=learner, actor_role="BARBER", limit=2
    )
    assert len(history) == 2
    assert all(set(item) == {"action", "result", "occurred_at"} for item in history)
