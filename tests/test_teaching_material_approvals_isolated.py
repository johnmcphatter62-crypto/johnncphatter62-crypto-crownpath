"""Owner-only material approval tests using synthetic disposable SQLite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User
from crownpath.curriculum_models import (
    CurriculumProgram, CurriculumCourse, CurriculumUnit, CurriculumLesson,
)
from crownpath.teaching_material_models import TeachingMaterial, TeachingMaterialVersion
from crownpath.teaching_material_approvals import owner_approve_teaching_material_version


def test_owner_approval_is_explicit_and_instructor_denied(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'material_approval.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Owner", email="approval-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Instructor",
                     email="approval-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Program",
                                  slug="approval-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="approval-course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit",
                                 title="Lesson", status="DRAFT"),
                TeachingMaterial(
                    material_id="material", lesson_id="lesson",
                    created_by_user_id="instructor", title="Official material",
                ),
                TeachingMaterialVersion(
                    version_id="version", material_id="material", version=1,
                    submitted_by_user_id="instructor", storage_key="synthetic/material/v1",
                    sha256_hex="a" * 64, byte_size=12, media_type="application/pdf",
                    approved=False,
                ),
            ])
            db.commit()
            with pytest.raises(PermissionError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="instructor", version_id="version"
                )
            assert db.get(TeachingMaterialVersion, "version").approved is False
            result = owner_approve_teaching_material_version(
                db, actor_user_id="owner", version_id="version"
            )
            assert result["approved"] is True
            assert result["approved_by_user_id"] == "owner"
            db.commit()
            with pytest.raises(ValueError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="owner", version_id="version"
                )
            db.get(User, "owner").active = False
            db.flush()
            with pytest.raises(PermissionError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="owner", version_id="version"
                )
    finally:
        engine.dispose()
