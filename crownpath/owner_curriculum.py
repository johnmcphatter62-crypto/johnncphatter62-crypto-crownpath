"""Owner-only curriculum draft service.

This module is intentionally not imported by CrownPath production startup yet.
It provides validated owner operations over the isolated curriculum models while
the curriculum migration remains unapplied in production.
"""
import re
import uuid

from sqlalchemy import select

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
    return {
        "programs": [program_dict(item) for item in programs],
        "courses": [course_dict(item) for item in courses],
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
