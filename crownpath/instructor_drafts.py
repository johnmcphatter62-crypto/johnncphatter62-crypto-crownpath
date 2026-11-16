"""Isolated instructor draft creation; no HTTP route or publishing capability."""
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from crownpath.curriculum_models import CurriculumLessonVersion
from crownpath.instructor_assignments import instructor_can_edit_lesson


def create_instructor_unapproved_draft(
    db: Session, *, instructor_user_id: str, lesson_id: str,
    content_json: str, version: int
) -> dict:
    """Create only an unapproved lesson version for an assigned draft lesson.

    The authorization check and write share one transaction. Caller commits.
    """
    if not instructor_can_edit_lesson(
        db, instructor_user_id=instructor_user_id, lesson_id=lesson_id
    ):
        raise PermissionError("Active assignment to a draft lesson required.")
    if version < 1:
        raise ValueError("Version must be 1 or greater.")
    if not isinstance(content_json, str) or not content_json.strip():
        raise ValueError("Lesson content is required.")
    if len(content_json.encode("utf-8")) > 65536:
        raise ValueError("Lesson content exceeds the 64 KiB draft limit.")
    try:
        parsed = json.loads(content_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Lesson content must be valid JSON.") from exc
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("Lesson content must be a nonempty JSON object.")
    duplicate = db.scalar(
        select(CurriculumLessonVersion).where(
            CurriculumLessonVersion.lesson_id == lesson_id,
            CurriculumLessonVersion.version == version,
        )
    )
    if duplicate is not None:
        raise ValueError("Lesson version already exists.")
    item = CurriculumLessonVersion(
        version_id=f"CP-ILVER-{uuid.uuid4().hex[:12].upper()}",
        lesson_id=lesson_id,
        version=version,
        content_json=content_json,
        source_type="CROWNPATH",
        approved=False,
        approved_by=None,
        approved_at=None,
    )
    db.add(item)
    db.flush()
    return {
        "version_id": item.version_id,
        "lesson_id": item.lesson_id,
        "version": item.version,
        "approved": item.approved,
    }
