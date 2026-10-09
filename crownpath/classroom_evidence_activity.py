"""Presentation-safe evidence activity summary for CrownPath classrooms.

This module does not expose an HTTP route or file storage references.
Authorization is inherited from the audited evidence history service.
"""
from crownpath.evidence_audit_view import evidence_revocation_history


def classroom_evidence_activity(db, *, evidence_id: str, actor_id: str, actor_role: str) -> dict:
    """Return a minimal learner-facing status and chronological activity."""
    history = evidence_revocation_history(
        db, evidence_id=evidence_id, actor_id=actor_id, actor_role=actor_role, limit=10
    )
    return {
        "evidence_id": evidence_id,
        "status": "REVOKED" if history else "NO_REVOCATION_RECORDED",
        "activities": [
            {
                "event": "EVIDENCE_REVOKED",
                "occurred_at": item["occurred_at"],
            }
            for item in history
        ],
    }
