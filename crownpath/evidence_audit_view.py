"""Privacy-minimized projection of authorized evidence revocation audit events.

No raw ORM objects, actor email, storage reference, or free-text audit reason
is exposed. The underlying audit access service enforces ownership/role.
"""
from crownpath.evidence_audit import list_evidence_revocation_audit


def evidence_revocation_history(db, *, evidence_id: str, actor_id: str, actor_role: str, limit: int = 25) -> list[dict]:
    """Return a bounded, allowlisted audit view for trusted backend callers."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Audit history limit must be between 1 and 100.")
    events = list_evidence_revocation_audit(
        db, evidence_id=evidence_id, actor_id=actor_id, actor_role=actor_role, limit=limit
    )
    return [
        {
            "action": event.action,
            "result": event.result,
            "occurred_at": event.created_at.isoformat(),
        }
        for event in events
    ]
