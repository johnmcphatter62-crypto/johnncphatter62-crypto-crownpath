"""Synthetic SQLite checks for official teaching material metadata.

No uploads, production databases, or live user accounts are involved.
"""
import hashlib

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User
from crownpath.curriculum_models import (
    CurriculumProgram, CurriculumCourse, CurriculumUnit, CurriculumLesson,
)
from crownpath.teaching_material_models import TeachingMaterial, TeachingMaterialVersion


def test_teaching_material_versions_persist_and_reject_duplicates(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'teaching_materials.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Owner", email="materials-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Instructor",
                     email="materials-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Program", slug="materials-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="materials-course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit",
                                 title="Lesson", status="DRAFT"),
            ])
            db.commit()
            db.add(TeachingMaterial(
                material_id="material", lesson_id="lesson",
                created_by_user_id="instructor", title="Scalp Care Lesson",
            ))
            db.add(TeachingMaterialVersion(
                version_id="version-1", material_id="material", version=1,
                submitted_by_user_id="instructor",
                storage_key="synthetic/material/version-1",
                sha256_hex=hashlib.sha256(b"synthetic content").hexdigest(),
                byte_size=len(b"synthetic content"),
                media_type="application/pdf", approved=False,
            ))
            db.commit()
        with Session(engine) as db:
            material = db.get(TeachingMaterial, "material")
            version = db.scalar(select(TeachingMaterialVersion).where(
                TeachingMaterialVersion.material_id == "material",
                TeachingMaterialVersion.version == 1,
            ))
            assert material.title == "Scalp Care Lesson"
            assert material.lesson_id == "lesson"
            assert version is not None
            assert version.approved is False
            assert version.approved_by_user_id is None
            assert version.sha256_hex == hashlib.sha256(b"synthetic content").hexdigest()
            db.add(TeachingMaterialVersion(
                version_id="version-duplicate", material_id="material", version=1,
                submitted_by_user_id="instructor",
                storage_key="synthetic/material/version-duplicate",
                sha256_hex="0" * 64, byte_size=1, media_type="application/pdf",
                approved=False,
            ))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
    finally:
        engine.dispose()
