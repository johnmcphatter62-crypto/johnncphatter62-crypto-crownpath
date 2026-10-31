"""Transactional, draft-only teaching-material version submission.

This helper does not upload files, expose downloads, or publish content.
The caller owns commit/rollback and must keep the authorization check and
write in the same database transaction.
"""
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from crownpath.teaching_material_models import TeachingMaterialVersion
from crownpath.teaching_material_permissions import can_submit_teaching_material_version

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def submit_unapproved_teaching_material_version(
    db: Session, *, actor_user_id: str, material_id: str, version: int,
    storage_key: str, sha256_hex: str, byte_size: int, media_type: str,
) -> dict:
    """Create metadata only when the active instructor is currently assigned."""
    if not can_submit_teaching_material_version(
        db, actor_user_id=actor_user_id, material_id=material_id
    ):
        raise PermissionError("Active instructor assignment to a draft lesson required.")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("Version must be a positive integer.")
    if not isinstance(storage_key, str) or not storage_key.startswith("synthetic/") or len(storage_key) > 200:
        raise ValueError("Only isolated synthetic storage keys are accepted.")
    if not isinstance(sha256_hex, str) or _SHA256.fullmatch(sha256_hex) is None:
        raise ValueError("Valid lowercase SHA-256 digest required.")
    if not isinstance(byte_size, int) or isinstance(byte_size, bool) or not (1 <= byte_size <= 10 * 1024 * 1024):
        raise ValueError("Invalid material byte size.")
    if media_type not in {"application/pdf", "text/plain", "image/png", "image/jpeg"}:
        raise ValueError("Unsupported material media type.")
    duplicate = db.scalar(select(TeachingMaterialVersion).where(
        TeachingMaterialVersion.material_id == material_id,
        TeachingMaterialVersion.version == version,
    ))
    if duplicate is not None:
        raise ValueError("Material version already exists.")
    record = TeachingMaterialVersion(
        version_id=f"CP-MATVER-{uuid.uuid4().hex[:12].upper()}",
        material_id=material_id,
        version=version,
        submitted_by_user_id=actor_user_id,
        storage_key=storage_key,
        sha256_hex=sha256_hex,
        byte_size=byte_size,
        media_type=media_type,
        approved=False,
        approved_by_user_id=None,
    )
    db.add(record)
    db.flush()
    return {"version_id": record.version_id, "material_id": material_id,
            "version": record.version, "approved": record.approved}
