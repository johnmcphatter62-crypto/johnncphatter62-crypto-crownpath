"""Seed the database curriculum hierarchy from CrownPath's existing catalog.

This bridge is intentionally idempotent: existing curriculum IDs are reused so
the legacy lesson experience can coexist with the database-backed curriculum.
"""
import json
import uuid

from sqlalchemy import select

from crownpath.curriculum_models import (
    CurriculumCourse,
    CurriculumLesson,
    CurriculumLessonVersion,
    CurriculumProgram,
    CurriculumUnit,
)
from crownpath.database import session
from crownpath.lesson_content import get_canonical_lesson_content


CATALOGS = {
    "HOME_CARE": [
        ("home-care-foundations", "Client Safety & Home Care Foundations"),
        ("home-care-sanitation", "Sanitation & Infection Control"),
        ("home-care-communication", "Professional Communication"),
        ("home-care-documentation", "Care Documentation"),
        ("wellness-client-experience", "Wellness Client Experience & Professional Boundaries"),
        ("avatar-bot-builder-foundations", "CrownPath Avatar & Bot Builder Foundations"),
    ],
    "BARBER": [
        ("barber-foundations", "Barbering Foundations"),
        ("barber-hair-scalp", "Hair & Scalp Science"),
        ("barber-scalp-camera-assessment", "Scalp Camera & AI-Assisted Cosmetic Assessment"),
        ("barber-cutting-grooming", "Cutting, Fading & Grooming"),
        ("barber-consultation-safety", "Client Consultation & Shop Safety"),
        ("wellness-client-experience", "Beauty & Wellness Client Experience"),
        ("wellness-fitness-foundations", "Fitness, Recovery & General Wellness Foundations"),
        ("avatar-bot-builder-foundations", "CrownPath Avatar & Bot Builder Foundations"),
    ],
    "COSMETOLOGY_PRO": [
        ("cosmetology-foundations", "Cosmetology Foundations"),
        ("cosmetology-hair-scalp", "Hair & Scalp Science"),
        ("cosmetology-scalp-camera-assessment", "Scalp Camera & AI-Assisted Cosmetic Assessment"),
        ("cosmetology-chemical-safety", "Chemical Services & Product Safety"),
        ("cosmetology-hair-replacement", "Non-Surgical Hair Replacement & Scalp Application"),
        ("cosmetology-makeup-artistry", "Professional Makeup Artistry"),
        ("cosmetology-nail-care", "Manicure & Pedicure Nail Care"),
        ("wellness-massage-foundations", "Wellness Massage Foundations & Scope Awareness"),
        ("wellness-fitness-foundations", "Fitness, Recovery & General Wellness Foundations"),
        ("wellness-client-experience", "Integrated Beauty & Wellness Client Experience"),
        ("avatar-bot-builder-foundations", "CrownPath Avatar & Bot Builder Foundations"),
    ],
}

PROGRAM_TITLES = {
    "HOME_CARE": "CrownPath Home Care",
    "BARBER": "CrownPath Barber",
    "COSMETOLOGY_PRO": "CrownPath Cosmetology, Beauty & Wellness",
}


def _id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def seed_legacy_curriculum():
    db = session()
    counts = {"programs": 0, "courses": 0, "units": 0, "lessons": 0, "versions": 0}
    try:
        for track, lessons in CATALOGS.items():
            slug = track.lower().replace("_", "-")
            program = db.scalar(select(CurriculumProgram).where(CurriculumProgram.slug == slug))
            if not program:
                program = CurriculumProgram(
                    program_id=_id("CP-PRG"),
                    title=PROGRAM_TITLES[track],
                    slug=slug,
                    description=f"Database-backed curriculum bridge for the {track} CrownPath pathway.",
                    status="DRAFT",
                )
                db.add(program); db.flush(); counts["programs"] += 1

            course = db.scalar(select(CurriculumCourse).where(
                CurriculumCourse.program_id == program.program_id,
                CurriculumCourse.slug == "core-foundations",
            ))
            if not course:
                course = CurriculumCourse(
                    course_id=_id("CP-CRS"), program_id=program.program_id,
                    title="Core Foundations", slug="core-foundations", sequence=1, status="DRAFT",
                )
                db.add(course); db.flush(); counts["courses"] += 1

            unit = db.scalar(select(CurriculumUnit).where(CurriculumUnit.course_id == course.course_id))
            if not unit:
                unit = CurriculumUnit(
                    unit_id=_id("CP-UNT"), course_id=course.course_id,
                    title="Pathway Lessons", sequence=1,
                    description="Existing CrownPath lessons migrated into the Curriculum Core.",
                )
                db.add(unit); db.flush(); counts["units"] += 1

            for sequence, (lesson_id, title) in enumerate(lessons, start=1):
                lesson = db.get(CurriculumLesson, lesson_id)
                if not lesson:
                    lesson = CurriculumLesson(
                        lesson_id=lesson_id, unit_id=unit.unit_id, title=title,
                        sequence=sequence, active_version=1, status="DRAFT",
                    )
                    db.add(lesson); db.flush(); counts["lessons"] += 1

                version = db.scalar(select(CurriculumLessonVersion).where(
                    CurriculumLessonVersion.lesson_id == lesson_id,
                    CurriculumLessonVersion.version == 1,
                ))
                if not version:
                    canonical = get_canonical_lesson_content(lesson_id)
                    if canonical:
                        db.add(CurriculumLessonVersion(
                            version_id=_id("CP-LV"), lesson_id=lesson_id, version=1,
                            content_json=json.dumps(canonical), source_type="CROWNPATH_LEGACY",
                            approved=False,
                        ))
                        counts["versions"] += 1
        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
