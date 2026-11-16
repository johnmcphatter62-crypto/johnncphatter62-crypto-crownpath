"""Synthetic SQLite Owner-only material review tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User
from crownpath.curriculum_models import (
    CurriculumProgram, CurriculumCourse, CurriculumUnit, CurriculumLesson,
)
from crownpath.teaching_material_models import TeachingMaterial, TeachingMaterialVersion
from crownpath.teaching_material_review import owner_review_teaching_material_version


def test_owner_review_is_read_only_and_instructor_denied(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'material_review.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Owner", email="review-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Instructor",
                     email="review-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Program",
                                  slug="review-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="review-course"),
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
            result = owner_review_teaching_material_version(
                db, actor_user_id="owner", version_id="version"
            )
            assert result["approved"] is False
            assert result["submitted_by_user_id"] == "instructor"
            assert "storage_key" not in result
            assert db.get(TeachingMaterialVersion, "version").approved is False
            for actor in ("instructor", "missing"):
                with pytest.raises(PermissionError):
                    owner_review_teaching_material_version(
                        db, actor_user_id=actor, version_id="version"
                    )
            db.get(User, "owner").active = False
            db.flush()
            with pytest.raises(PermissionError):
                owner_review_teaching_material_version(
                    db, actor_user_id="owner", version_id="version"
                )
    finally:
        engine.dispose()
