"""Owner-only curriculum draft service.

This module is intentionally not imported by CrownPath production startup yet.
It provides validated owner operations over the isolated curriculum models while
the curriculum migration remains unapplied in production.
"""
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from crownpath.models import AuditEvent
from crownpath.curriculum_models import (
    CurriculumCourse,
    CurriculumLesson,
    CurriculumLessonVersion,
    CurriculumProgram,
    CurriculumUnit,
)


DRAFT_STATUS = "DRAFT"
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def require_owner(user: dict) -> None:
    if not user or not user.get("active") or user.get("role", "").upper() != "OWNER":
        raise PermissionError("Owner access required.")


def validate_slug(slug: str) -> str:
    value = slug.strip().lower()
    if not _SLUG_RE.fullmatch(value):
        raise ValueError("Slug must contain lowercase letters, numbers, and single hyphens only.")
    return value


def program_dict(item: CurriculumProgram) -> dict:
    return {
        "program_id": item.program_id,
        "title": item.title,
        "slug": item.slug,
        "description": item.description,
        "status": item.status,
    }


def unit_dict(item: CurriculumUnit) -> dict:
    return {"unit_id": item.unit_id, "course_id": item.course_id, "title": item.title, "description": item.description, "sequence": item.sequence}


def lesson_dict(item: CurriculumLesson) -> dict:
    return {"lesson_id": item.lesson_id, "unit_id": item.unit_id, "title": item.title, "sequence": item.sequence, "active_version": item.active_version, "status": item.status}


def course_dict(item: CurriculumCourse) -> dict:
    return {
        "course_id": item.course_id,
        "program_id": item.program_id,
        "title": item.title,
        "slug": item.slug,
        "description": item.description,
        "sequence": item.sequence,
        "status": item.status,
    }


def list_structure(db, user: dict) -> dict:
    require_owner(user)
    programs = db.scalars(select(CurriculumProgram).order_by(CurriculumProgram.title)).all()
    courses = db.scalars(select(CurriculumCourse).order_by(CurriculumCourse.program_id, CurriculumCourse.sequence)).all()
    units = db.scalars(select(CurriculumUnit).order_by(CurriculumUnit.course_id, CurriculumUnit.sequence)).all()
    lessons = db.scalars(select(CurriculumLesson).order_by(CurriculumLesson.unit_id, CurriculumLesson.sequence)).all()
    return {
        "programs": [program_dict(item) for item in programs],
        "courses": [course_dict(item) for item in courses],
        "units": [unit_dict(item) for item in units],
        "lessons": [lesson_dict(item) for item in lessons],
    }


def create_draft_program(db, user: dict, *, title: str, slug: str, description: str | None = None) -> dict:
    require_owner(user)
    clean_title = title.strip()
    if len(clean_title) < 2 or len(clean_title) > 200:
        raise ValueError("Program title must be between 2 and 200 characters.")
    clean_slug = validate_slug(slug)
    if db.scalar(select(CurriculumProgram).where(CurriculumProgram.slug == clean_slug)):
        raise ValueError("Program slug already exists.")

    item = CurriculumProgram(
        program_id=f"CP-PROG-{uuid.uuid4().hex[:12].upper()}",
        title=clean_title,
        slug=clean_slug,
        description=(description or "").strip() or None,
        status=DRAFT_STATUS,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return program_dict(item)


def _clean_title(title: str, kind: str) -> str:
    value = title.strip()
    if len(value) < 2 or len(value) > 200:
        raise ValueError(f"{kind} title must be between 2 and 200 characters.")
    return value


def _positive_sequence(sequence: int) -> int:
    if sequence < 1:
        raise ValueError("Sequence must be 1 or greater.")
    return sequence


def create_draft_course(db, user: dict, *, program_id: str, title: str, slug: str, description: str | None = None, sequence: int = 1) -> dict:
    require_owner(user)
    if not db.get(CurriculumProgram, program_id):
        raise ValueError("Program not found.")
    clean_slug = validate_slug(slug)
    duplicate = db.scalar(select(CurriculumCourse).where(CurriculumCourse.program_id == program_id, CurriculumCourse.slug == clean_slug))
    if duplicate:
        raise ValueError("Course slug already exists in this program.")
    item = CurriculumCourse(
        course_id=f"CP-COURSE-{uuid.uuid4().hex[:12].upper()}",
        program_id=program_id,
        title=_clean_title(title, "Course"),
        slug=clean_slug,
        description=(description or "").strip() or None,
        sequence=_positive_sequence(sequence),
        status=DRAFT_STATUS,
    )
    db.add(item); db.commit(); db.refresh(item)
    return course_dict(item)


def create_draft_unit(db, user: dict, *, course_id: str, title: str, description: str | None = None, sequence: int = 1) -> dict:
    require_owner(user)
    if not db.get(CurriculumCourse, course_id):
        raise ValueError("Course not found.")
    item = CurriculumUnit(
        unit_id=f"CP-UNIT-{uuid.uuid4().hex[:12].upper()}",
        course_id=course_id,
        title=_clean_title(title, "Unit"),
        description=(description or "").strip() or None,
        sequence=_positive_sequence(sequence),
    )
    db.add(item); db.commit(); db.refresh(item)
    return {"unit_id": item.unit_id, "course_id": item.course_id, "title": item.title, "description": item.description, "sequence": item.sequence}


def create_draft_lesson(db, user: dict, *, unit_id: str, title: str, lesson_id: str | None = None, sequence: int = 1) -> dict:
    require_owner(user)
    if not db.get(CurriculumUnit, unit_id):
        raise ValueError("Unit not found.")
    item = CurriculumLesson(
        lesson_id=lesson_id or f"CP-LESSON-{uuid.uuid4().hex[:12].upper()}",
        unit_id=unit_id,
        title=_clean_title(title, "Lesson"),
        sequence=_positive_sequence(sequence),
        active_version=1,
        status=DRAFT_STATUS,
    )
    db.add(item); db.commit(); db.refresh(item)
    return {"lesson_id": item.lesson_id, "unit_id": item.unit_id, "title": item.title, "sequence": item.sequence, "active_version": item.active_version, "status": item.status}


def create_unapproved_lesson_version(db, user: dict, *, lesson_id: str, content_json: str, version: int) -> dict:
    require_owner(user)
    if not db.get(CurriculumLesson, lesson_id):
        raise ValueError("Lesson not found.")
    if version < 1:
        raise ValueError("Version must be 1 or greater.")
    if not content_json.strip():
        raise ValueError("Lesson content is required.")
    duplicate = db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id == lesson_id, CurriculumLessonVersion.version == version))
    if duplicate:
        raise ValueError("Lesson version already exists.")
    item = CurriculumLessonVersion(
        version_id=f"CP-LVER-{uuid.uuid4().hex[:12].upper()}",
        lesson_id=lesson_id,
        version=version,
        content_json=content_json,
        source_type="CROWNPATH",
        approved=False,
        approved_by=None,
        approved_at=None,
    )
    db.add(item); db.commit(); db.refresh(item)
    return {"version_id": item.version_id, "lesson_id": item.lesson_id, "version": item.version, "approved": item.approved}


def list_lesson_versions_for_review(db, user: dict, *, lesson_id: str) -> list[dict]:
    require_owner(user)
    if not db.get(CurriculumLesson, lesson_id):
        raise ValueError("Lesson not found.")
    items = db.scalars(
        select(CurriculumLessonVersion)
        .where(CurriculumLessonVersion.lesson_id == lesson_id)
        .order_by(CurriculumLessonVersion.version.desc())
    ).all()
    return [
        {
            "version_id": item.version_id,
            "lesson_id": item.lesson_id,
            "version": item.version,
            "source_type": item.source_type,
            "approved": item.approved,
            "approved_by": item.approved_by,
            "approved_at": item.approved_at,
            "created_at": item.created_at,
        }
        for item in items
    ]


def approve_lesson_version(db, user: dict, *, version_id: str) -> dict:
    require_owner(user)
    item = db.get(CurriculumLessonVersion, version_id)
    if not item:
        raise ValueError("Lesson version not found.")
    lesson = db.get(CurriculumLesson, item.lesson_id)
    if not lesson:
        raise ValueError("Lesson not found.")
    if item.approved:
        raise ValueError("Lesson version is already approved.")
    if lesson.status != DRAFT_STATUS:
        raise ValueError("Only draft lessons can receive version approval.")

    item.approved = True
    item.approved_by = user["user_id"]
    item.approved_at = datetime.now(timezone.utc)
    lesson.active_version = item.version
    db.add(AuditEvent(
        user_id=user["user_id"],
        action="CURRICULUM_LESSON_VERSION_APPROVED",
        category="CURRICULUM",
        resource_type="CURRICULUM_LESSON_VERSION",
        resource_id=item.version_id,
        result="SUCCESS",
        reason=f"Owner approved lesson {item.lesson_id} version {item.version}.",
    ))
    db.commit()
    db.refresh(item)
    return {
        "version_id": item.version_id,
        "lesson_id": item.lesson_id,
        "version": item.version,
        "approved": item.approved,
        "approved_by": item.approved_by,
        "approved_at": item.approved_at,
        "lesson_status": lesson.status,
    }


def list_approval_history(db, user: dict, *, limit: int = 50) -> list[dict]:
    require_owner(user)
    safe_limit = max(1, min(int(limit), 100))
    items = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.category == "CURRICULUM",
            AuditEvent.action == "CURRICULUM_LESSON_VERSION_APPROVED",
        )
        .order_by(AuditEvent.audit_id.desc())
        .limit(safe_limit)
    ).all()
    return [
        {
            "audit_id": item.audit_id,
            "user_id": item.user_id,
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "result": item.result,
            "reason": item.reason,
            "created_at": item.created_at,
        }
        for item in items
    ]


def curriculum_readiness(db, user: dict) -> dict:
    """Report Owner-only draft readiness without publishing or mutating curriculum."""
    require_owner(user)
    programs = db.scalars(select(CurriculumProgram)).all()
    courses = db.scalars(select(CurriculumCourse)).all()
    units = db.scalars(select(CurriculumUnit)).all()
    lessons = db.scalars(select(CurriculumLesson)).all()
    versions = db.scalars(select(CurriculumLessonVersion)).all()

    approved_versions = [item for item in versions if item.approved]
    lessons_with_versions = {item.lesson_id for item in versions}
    lessons_with_approved_versions = {item.lesson_id for item in approved_versions}

    checks = [
        {"key": "programs", "label": "At least one draft program", "ready": bool(programs), "count": len(programs)},
        {"key": "courses", "label": "At least one draft course", "ready": bool(courses), "count": len(courses)},
        {"key": "units", "label": "At least one curriculum unit", "ready": bool(units), "count": len(units)},
        {"key": "lessons", "label": "At least one draft lesson", "ready": bool(lessons), "count": len(lessons)},
        {"key": "versions", "label": "Every lesson has a saved version", "ready": bool(lessons) and all(item.lesson_id in lessons_with_versions for item in lessons), "count": len(versions)},
        {"key": "approvals", "label": "Every lesson has an Owner-approved version", "ready": bool(lessons) and all(item.lesson_id in lessons_with_approved_versions for item in lessons), "count": len(approved_versions)},
    ]
    missing = [item["label"] for item in checks if not item["ready"]]
    return {
        "ready_for_activation_review": not missing,
        "activation_performed": False,
        "learner_publishing_enabled": False,
        "checks": checks,
        "missing": missing,
    }
