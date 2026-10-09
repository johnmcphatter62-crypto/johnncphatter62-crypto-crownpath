"""Presentation-safe evidence activity summary for CrownPath classrooms.

This module does not expose an HTTP route or file storage references.
Authorization is inherited from the audited evidence history service.
"""
from crownpath.evidence_audit_view import evidence_revocation_history
from crownpath.models import AssessmentEvidenceRecord, EvidenceStorageObject


def classroom_evidence_activity(db, *, evidence_id: str, actor_id: str, actor_role: str) -> dict:
    """Return a minimal learner-facing status and chronological activity."""
    history = evidence_revocation_history(
        db, evidence_id=evidence_id, actor_id=actor_id, actor_role=actor_role, limit=10
    )
    record = db.get(AssessmentEvidenceRecord, evidence_id)
    storage = db.get(EvidenceStorageObject, record.storage_reference)
    is_revoked = bool(record.revoked or (storage is not None and storage.revoked))
    return {
        "evidence_id": evidence_id,
        "status": "REVOKED" if is_revoked else "ACTIVE",
        "activities": [
            {
                "event": "EVIDENCE_REVOKED",
                "occurred_at": item["occurred_at"],
            }
            for item in history
        ],
    }
