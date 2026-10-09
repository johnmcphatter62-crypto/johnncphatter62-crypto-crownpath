"""Trusted transactional entry point for assessment evidence revocation.

Callers must authenticate the request before supplying actor_id and actor_role.
This module does not create a public API endpoint.
"""
from crownpath.evidence_revocation import revoke_evidence


def commit_evidence_revocation(db, *, evidence_id: str, actor_id: str, actor_role: str) -> bool:
    """Atomically commit the revocation and audit event, or roll both back."""
    try:
        changed = revoke_evidence(
            db, evidence_id=evidence_id, actor_id=actor_id, actor_role=actor_role
        )
        db.commit()
        return changed
    except Exception:
        db.rollback()
        raise
