"""Fail-closed authorization for official teaching-material metadata.

No HTTP endpoints or file storage are enabled by this module.
"""
from sqlalchemy.orm import Session

from crownpath.instructor_assignments import instructor_can_edit_lesson
from crownpath.models import User
from crownpath.teaching_material_models import TeachingMaterial


def can_submit_teaching_material_version(
    db: Session, *, actor_user_id: str, material_id: str
) -> bool:
    """Only an active assigned instructor may submit a draft version."""
    actor = db.get(User, actor_user_id)
    material = db.get(TeachingMaterial, material_id)
    if actor is None or material is None or not actor.active:
        return False
    if actor.role != "INSTRUCTOR":
        return False
    return instructor_can_edit_lesson(
        db, instructor_user_id=actor_user_id, lesson_id=material.lesson_id
    )


def can_owner_review_teaching_material(
    db: Session, *, actor_user_id: str, material_id: str
) -> bool:
    """Only an active Owner may review official material metadata."""
    actor = db.get(User, actor_user_id)
    material = db.get(TeachingMaterial, material_id)
    return bool(
        actor is not None and actor.active and actor.role == "OWNER"
        and material is not None
    )
