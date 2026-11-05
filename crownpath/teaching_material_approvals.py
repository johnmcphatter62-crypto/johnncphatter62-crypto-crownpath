"""Explicit Owner-only approval for synthetic teaching-material metadata.

No publishing, HTTP endpoint, file storage, or production changes.
Caller controls transaction commit/rollback.
"""
from sqlalchemy import update
from sqlalchemy.orm import Session

from crownpath.models import AuditEvent
from crownpath.teaching_material_models import TeachingMaterialVersion
from crownpath.teaching_material_permissions import can_owner_review_teaching_material


def owner_approve_teaching_material_version(
    db: Session, *, actor_user_id: str, version_id: str
) -> dict:
    version = db.get(TeachingMaterialVersion, version_id)
    if version is None or not can_owner_review_teaching_material(
        db, actor_user_id=actor_user_id, material_id=version.material_id
    ):
        raise PermissionError("Active Owner authorization required.")
    # Conditional update prevents two concurrent requests from both winning
    # the same unapproved -> approved transition.
    updated = db.execute(
        update(TeachingMaterialVersion)
        .where(
            TeachingMaterialVersion.version_id == version_id,
            TeachingMaterialVersion.approved.is_(False),
        )
        .values(approved=True, approved_by_user_id=actor_user_id)
        .execution_options(synchronize_session="fetch")
    )
    if updated.rowcount != 1:
        raise ValueError("Material version is already approved.")
    db.refresh(version)
    db.add(AuditEvent(
        user_id=actor_user_id,
        action="teaching_material.version.approve",
        category="curriculum",
        resource_type="teaching_material_version",
        resource_id=version.version_id,
        result="SUCCESS",
        reason="Explicit Owner approval of unapproved material metadata",
    ))
    db.flush()
    return {
        "version_id": version.version_id,
        "material_id": version.material_id,
        "approved": version.approved,
        "approved_by_user_id": version.approved_by_user_id,
    }
