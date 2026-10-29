"""Disposable SQLite tests for draft-only teaching-material submissions."""
import hashlib

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, InstructorCourseAssignment
from crownpath.curriculum_models import (
    CurriculumProgram, CurriculumCourse, CurriculumUnit, CurriculumLesson,
)
from crownpath.teaching_material_models import TeachingMaterial, TeachingMaterialVersion
from crownpath.teaching_material_submissions import submit_unapproved_teaching_material_version


def test_material_submission_denies_revoked_assignment(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'material_submission.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Owner", email="submission-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Instructor",
                     email="submission-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Program",
                                  slug="submission-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="submission-course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit",
                                 title="Lesson", status="DRAFT"),
                InstructorCourseAssignment(
                    assignment_id="assignment", instructor_user_id="instructor",
                    course_id="course", assigned_by_user_id="owner", active=True,
                ),
                TeachingMaterial(
                    material_id="material", lesson_id="lesson",
                    created_by_user_id="instructor", title="Official teaching material",
                ),
            ])
            db.commit()
            kwargs = dict(
                actor_user_id="instructor", material_id="material", version=1,
                storage_key="synthetic/material/v1",
                sha256_hex=hashlib.sha256(b"synthetic file").hexdigest(),
                byte_size=len(b"synthetic file"), media_type="application/pdf",
            )
            created = submit_unapproved_teaching_material_version(db, **kwargs)
            assert created["approved"] is False
            db.commit()
            stored = db.get(TeachingMaterialVersion, created["version_id"])
            assert stored is not None
            assert stored.approved is False
            assert stored.approved_by_user_id is None

            db.get(InstructorCourseAssignment, "assignment").active = False
            db.commit()
            with pytest.raises(PermissionError):
                submit_unapproved_teaching_material_version(
                    db, **{**kwargs, "version": 2, "storage_key": "synthetic/material/v2"}
                )
            assert db.scalar(select(TeachingMaterialVersion).where(
                TeachingMaterialVersion.material_id == "material",
                TeachingMaterialVersion.version == 2,
            )) is None

            with pytest.raises(PermissionError):
                submit_unapproved_teaching_material_version(
                    db, **{**kwargs, "actor_user_id": "owner", "version": 3,
                           "storage_key": "synthetic/material/v3"}
                )
    finally:
        engine.dispose()
