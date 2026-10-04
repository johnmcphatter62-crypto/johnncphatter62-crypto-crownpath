"""Owner-only curriculum draft service.

This module is intentionally not imported by CrownPath production startup yet.
It provides validated owner operations over the isolated curriculum models while
the curriculum migration remains unapplied in production.
"""
import re
import uuid

from sqlalchemy import select

from crownpath.curriculum_models import CurriculumCourse, CurriculumProgram


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
