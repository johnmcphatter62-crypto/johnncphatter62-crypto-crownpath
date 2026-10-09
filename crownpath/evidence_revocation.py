"""Transactional evidence revocation for trusted backend callers.

This service is not an HTTP endpoint. Authorization must be performed by the
caller; only a server-authenticated owner or authorized administrator may invoke.
"""
from sqlalchemy import select

from crownpath.models import AssessmentEvidenceRecord, AuditEvent, EvidenceStorageObject, User


class EvidenceRevocationDenied(ValueError):
    pass


def revoke_evidence(db, *, evidence_id: str, actor_id: str, actor_role: str):
    """Stage revocation and audit in one transaction; caller commits or rolls back."""
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise EvidenceRevocationDenied("Evidence ID required.")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise EvidenceRevocationDenied("Authenticated actor required.")
    if not isinstance(actor_role, str) or not actor_role.strip():
        raise EvidenceRevocationDenied("Actor role required.")
    actor = db.get(User, actor_id)
    if actor is None or not actor.active or actor.role != actor_role:
        raise EvidenceRevocationDenied("Active actor identity and role required.")
    record = db.scalar(
        select(AssessmentEvidenceRecord).where(
            AssessmentEvidenceRecord.evidence_id == evidence_id
        ).with_for_update()
    )
    if record is None:
        raise EvidenceRevocationDenied("Evidence not found.")
    if actor_id != record.learner_id and actor.role != "ADMIN":
        raise EvidenceRevocationDenied("Not authorized to revoke evidence.")
    storage = db.scalar(
        select(EvidenceStorageObject).where(
            EvidenceStorageObject.storage_reference == record.storage_reference
        ).with_for_update()
    )
    if (storage is None or storage.learner_id != record.learner_id
            or storage.lesson_id != record.lesson_id
            or storage.evidence_type != record.evidence_type):
        raise EvidenceRevocationDenied("Trusted storage metadata missing or mismatched.")
    if record.revoked and storage.revoked:
        return False
    record.revoked = True
    storage.revoked = True
    db.add(AuditEvent(
        user_id=actor_id,
        action="ASSESSMENT_EVIDENCE_REVOKED",
        category="ASSESSMENT",
        resource_type="EVIDENCE",
        resource_id=evidence_id,
        result="SUCCESS",
    ))
    return True
