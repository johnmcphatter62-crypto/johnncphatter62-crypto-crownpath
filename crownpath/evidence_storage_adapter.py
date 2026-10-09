"""Trusted backend storage adapter boundary for assessment evidence.

Implementations must retrieve metadata from authenticated server-side storage.
Never build this adapter from client-supplied metadata or public object URLs.
"""
from typing import Protocol, Mapping, Any

from crownpath.evidence_registration import stage_evidence_registration
from crownpath.evidence_storage_verification import EvidenceStorageVerificationDenied


class TrustedEvidenceStorage(Protocol):
    def get_verified_metadata(self, storage_reference: str) -> Mapping[str, Any] | None:
        """Return authoritative metadata from a trusted storage backend."""


def register_evidence_from_storage(
    db, *, storage: TrustedEvidenceStorage, authenticated_learner: dict,
    lesson_id: str, evidence_type: str, storage_reference: str,
    consent_confirmed: bool = False,
):
    """Stage evidence after server-side metadata retrieval; caller owns commit."""
    if not isinstance(storage_reference, str) or not storage_reference.strip():
        raise EvidenceStorageVerificationDenied("Storage reference required.")
    metadata = storage.get_verified_metadata(storage_reference)
    if not isinstance(metadata, Mapping):
        raise EvidenceStorageVerificationDenied("Trusted storage object not found.")
    return stage_evidence_registration(
        db,
        authenticated_learner=authenticated_learner,
        lesson_id=lesson_id,
        evidence_type=evidence_type,
        verified_storage_reference=storage_reference,
        consent_confirmed=consent_confirmed,
        trusted_storage_metadata=dict(metadata),
    )


def commit_evidence_registration(db, **kwargs):
    """Commit the staged record atomically; rollback on failure."""
    try:
        record = register_evidence_from_storage(db, **kwargs)
        db.commit()
        return record
    except Exception:
        db.rollback()
        raise
