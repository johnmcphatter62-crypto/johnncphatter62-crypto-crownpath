"""Fail-closed validation of evidence storage metadata from a trusted backend.

This module does not authenticate remote storage itself. Its caller must
retrieve the metadata from a trusted storage adapter, never from client input.
"""


class EvidenceStorageVerificationDenied(ValueError):
    pass


def verify_storage_metadata(
    *, learner_id: str, lesson_id: str, evidence_type: str,
    storage_reference: str, trusted_metadata: dict | None,
) -> str:
    if not isinstance(trusted_metadata, dict):
        raise EvidenceStorageVerificationDenied("Trusted storage metadata is required.")
    if trusted_metadata.get("learner_id") != learner_id:
        raise EvidenceStorageVerificationDenied("Storage learner mismatch.")
    if trusted_metadata.get("lesson_id") != lesson_id:
        raise EvidenceStorageVerificationDenied("Storage lesson mismatch.")
    if trusted_metadata.get("evidence_type") != evidence_type:
        raise EvidenceStorageVerificationDenied("Storage evidence type mismatch.")
    if trusted_metadata.get("storage_reference") != storage_reference:
        raise EvidenceStorageVerificationDenied("Storage reference mismatch.")
    if trusted_metadata.get("upload_complete") is not True:
        raise EvidenceStorageVerificationDenied("Upload has not been verified complete.")
    if trusted_metadata.get("revoked") is not False:
        raise EvidenceStorageVerificationDenied("Storage object is revoked or unknown.")
    return storage_reference
