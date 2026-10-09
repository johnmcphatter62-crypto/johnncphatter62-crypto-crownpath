"""Read-only, scoped audit access for trusted CrownPath backend callers.

Never accepts arbitrary learner IDs as authorization. Actor identity is
resolved from the persisted user account; no public HTTP route is provided.
"""
from sqlalchemy import select

from crownpath.models import AssessmentEvidenceRecord, AuditEvent, User


class EvidenceAuditAccessDenied(ValueError):
    pass


def list_evidence_revocation_audit(db, *, evidence_id: str, actor_id: str, actor_role: str, limit: int = 25):
    """Return chronological revocation events for an owner or active admin."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Audit history limit must be between 1 and 100.")
    if not isinstance(evidence_id, str) or not evidence_id.strip() or len(evidence_id) > 64:
        raise EvidenceAuditAccessDenied("Valid evidence ID required.")
    if not isinstance(actor_id, str) or not actor_id.strip() or not isinstance(actor_role, str):
        raise EvidenceAuditAccessDenied("Authenticated actor required.")
    actor = db.get(User, actor_id)
    if actor is None or not actor.active or actor.role != actor_role:
        raise EvidenceAuditAccessDenied("Active actor identity and role required.")
    evidence = db.get(AssessmentEvidenceRecord, evidence_id)
    if evidence is None or (evidence.learner_id != actor_id and actor.role != "ADMIN"):
        raise EvidenceAuditAccessDenied("Evidence audit not accessible.")
    return db.scalars(
        select(AuditEvent).where(
            AuditEvent.resource_id == evidence_id,
            AuditEvent.resource_type == "EVIDENCE",
            AuditEvent.category == "ASSESSMENT",
            AuditEvent.action == "ASSESSMENT_EVIDENCE_REVOKED",
            AuditEvent.result == "SUCCESS",
        ).order_by(AuditEvent.created_at.desc(), AuditEvent.audit_id.desc()).limit(limit)
    ).all()[::-1]
