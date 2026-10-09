"""Read-only server-side evidence ownership lookup.

Caller supplies a trusted SQLAlchemy session; client-provided owner mappings
must never be used. This module does not upload files or issue approvals.
"""
from sqlalchemy import select

from crownpath.models import AssessmentEvidenceRecord


def lookup_verified_evidence_owners(db, *, learner_id: str, lesson_id: str, references: list[str]) -> dict[str, str]:
    if not learner_id or not lesson_id or not references:
        return {}
    if len(references) != len(set(references)):
        return {}
    records = db.scalars(
        select(AssessmentEvidenceRecord).where(
            AssessmentEvidenceRecord.evidence_id.in_(references),
            AssessmentEvidenceRecord.learner_id == learner_id,
            AssessmentEvidenceRecord.lesson_id == lesson_id,
            AssessmentEvidenceRecord.revoked.is_(False),
        )
    ).all()
    verified = {}
    for record in records:
        if record.evidence_type in {"PHOTO", "VIDEO"} and not record.consent_confirmed:
            continue
        verified[record.evidence_id] = record.learner_id
    return verified
