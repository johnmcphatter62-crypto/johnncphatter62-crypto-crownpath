"""Owner-only review of synthetic teaching-material metadata.

No HTTP route, object download, publication, or production change.
"""
from sqlalchemy.orm import Session

from crownpath.teaching_material_models import TeachingMaterial, TeachingMaterialVersion
from crownpath.teaching_material_permissions import can_owner_review_teaching_material


def owner_review_teaching_material_version(
    db: Session, *, actor_user_id: str, version_id: str
) -> dict:
    """Return minimal metadata only after verifying active Owner authorization."""
    version = db.get(TeachingMaterialVersion, version_id)
    if version is None or not can_owner_review_teaching_material(
        db, actor_user_id=actor_user_id, material_id=version.material_id
    ):
        raise PermissionError("Active Owner access to this material required.")
    material = db.get(TeachingMaterial, version.material_id)
    if material is None:
        raise PermissionError("Material unavailable.")
    return {
        "material_id": material.material_id,
        "lesson_id": material.lesson_id,
        "title": material.title,
        "version_id": version.version_id,
        "version": version.version,
        "submitted_by_user_id": version.submitted_by_user_id,
        "sha256_hex": version.sha256_hex,
        "byte_size": version.byte_size,
        "media_type": version.media_type,
        "approved": version.approved,
    }
