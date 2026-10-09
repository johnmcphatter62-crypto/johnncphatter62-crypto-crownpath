"""PostgreSQL tests for classroom evidence activity summaries."""
import pytest

from crownpath.classroom_evidence_activity import classroom_evidence_activity
from crownpath.evidence_audit import EvidenceAuditAccessDenied
from crownpath.evidence_revocation import revoke_evidence
from test_evidence_registry_postgres import evidence_db, add_evidence


def test_classroom_activity_reflects_live_revocation_status(evidence_db):
    db, learner, other, suffix = evidence_db
    ref = f"classroom-{suffix}"
    add_evidence(db, ref, learner)
    initial = classroom_evidence_activity(
        db, evidence_id=ref, actor_id=learner, actor_role="BARBER"
    )
    assert initial == {"evidence_id": ref, "status": "ACTIVE", "activities": []}
    revoke_evidence(db, evidence_id=ref, actor_id=learner, actor_role="BARBER")
    db.flush()
    updated = classroom_evidence_activity(
        db, evidence_id=ref, actor_id=learner, actor_role="BARBER"
    )
    assert updated["status"] == "REVOKED"
    assert len(updated["activities"]) == 1
    assert set(updated["activities"][0]) == {"event", "occurred_at"}
    assert "storage_reference" not in str(updated)
    with pytest.raises(EvidenceAuditAccessDenied):
        classroom_evidence_activity(
            db, evidence_id=ref, actor_id=other, actor_role="BARBER"
        )


def test_classroom_activity_does_not_leak_missing_evidence(evidence_db):
    db, learner, _, suffix = evidence_db
    with pytest.raises(EvidenceAuditAccessDenied):
        classroom_evidence_activity(
            db, evidence_id=f"missing-{suffix}", actor_id=learner, actor_role="BARBER"
        )
