"""Server-controlled metadata registration for assessment evidence.

This service only stages metadata. A trusted caller must authenticate the
learner and verify that the storage reference was issued by the upload store.
No file bytes are uploaded and no credential is issued.
"""
from uuid import uuid4

from crownpath.models import AssessmentEvidenceRecord

ALLOWED_TYPES = frozenset({"OBSERVATION_NOTE", "PHOTO", "VIDEO", "DOCUMENT"})


class EvidenceRegistrationDenied(ValueError):
    pass


def stage_evidence_registration(
    db, *, authenticated_learner: dict, lesson_id: str,
    evidence_type: str, verified_storage_reference: str,
    consent_confirmed: bool = False,
):
    learner_id = authenticated_learner.get("user_id") if isinstance(authenticated_learner, dict) else None
    role = authenticated_learner.get("role", "").upper() if isinstance(authenticated_learner, dict) else ""
    if not learner_id or not authenticated_learner.get("active") or role not in {"HOME_CARE", "BARBER", "COSMETOLOGY_PRO"}:
        raise EvidenceRegistrationDenied("Active learner authentication required.")
    if not isinstance(lesson_id, str) or not lesson_id.strip() or len(lesson_id) > 100:
        raise EvidenceRegistrationDenied("Valid lesson ID required.")
    if evidence_type not in ALLOWED_TYPES:
        raise EvidenceRegistrationDenied("Unsupported evidence type.")
    if not isinstance(verified_storage_reference, str) or not verified_storage_reference.strip() or len(verified_storage_reference) > 255:
        raise EvidenceRegistrationDenied("Verified storage reference required.")
    if any(ord(char) < 32 for char in verified_storage_reference):
        raise EvidenceRegistrationDenied("Invalid storage reference.")
    if not isinstance(consent_confirmed, bool):
        raise EvidenceRegistrationDenied("Consent flag must be boolean.")
    if evidence_type in {"PHOTO", "VIDEO"} and not consent_confirmed:
        raise EvidenceRegistrationDenied("Explicit media consent confirmation required.")
    record = AssessmentEvidenceRecord(
        evidence_id=f"ev-{uuid4().hex}",
        learner_id=learner_id,
        lesson_id=lesson_id,
        evidence_type=evidence_type,
        storage_reference=verified_storage_reference,
        consent_confirmed=consent_confirmed,
        revoked=False,
    )
    db.add(record)
    return record
