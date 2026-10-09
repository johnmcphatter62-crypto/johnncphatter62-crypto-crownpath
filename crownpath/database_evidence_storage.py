"""Database-backed trusted storage metadata adapter.

This is a local metadata registry, not a remote object-storage connector.
Only backend processes with appropriate authorization may create these rows.
"""
from sqlalchemy import select

from crownpath.models import EvidenceStorageObject


class DatabaseEvidenceStorage:
    def __init__(self, db):
        self.db = db

    def get_verified_metadata(self, storage_reference: str):
        if not isinstance(storage_reference, str) or not storage_reference.strip():
            return None
        obj = self.db.scalar(
            select(EvidenceStorageObject).where(
                EvidenceStorageObject.storage_reference == storage_reference
            )
        )
        if obj is None:
            return None
        return {
            "learner_id": obj.learner_id,
            "lesson_id": obj.lesson_id,
            "evidence_type": obj.evidence_type,
            "storage_reference": obj.storage_reference,
            "upload_complete": obj.upload_complete,
            "revoked": obj.revoked,
        }
