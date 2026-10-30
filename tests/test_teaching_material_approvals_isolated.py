"""Owner-only material approval tests using synthetic disposable SQLite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuditEvent
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
            assert db.query(AuditEvent).filter_by(
                action="teaching_material.version.approve"
            ).count() == 0
            with pytest.raises(PermissionError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="instructor", version_id="nonexistent"
                )
            assert db.query(AuditEvent).filter_by(
                action="teaching_material.version.approve"
            ).count() == 0
            result = owner_approve_teaching_material_version(
                db, actor_user_id="owner", version_id="version"
            )
            assert result["approved"] is True
            assert result["approved_by_user_id"] == "owner"
            db.commit()
            events = db.query(AuditEvent).filter_by(
                action="teaching_material.version.approve",
                resource_id="version", result="SUCCESS",
            ).all()
            assert len(events) == 1
            assert events[0].user_id == "owner"
            assert events[0].created_at is not None
            with pytest.raises(ValueError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="owner", version_id="version"
                )
            assert db.query(AuditEvent).filter_by(
                action="teaching_material.version.approve"
            ).count() == 1
            db.get(User, "owner").active = False
            db.flush()
            with pytest.raises(PermissionError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="owner", version_id="version"
                )
            assert db.query(AuditEvent).filter_by(
                action="teaching_material.version.approve"
            ).count() == 1
            assert db.get(TeachingMaterialVersion, "version").approved_by_user_id == "owner"
    finally:
        engine.dispose()


def test_owner_approval_and_audit_roll_back_together(tmp_path):
    """An uncommitted approval must not survive transaction rollback."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'material_rollback.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="rollback-owner", name="Owner",
                     email="rollback-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="rollback-instructor", name="Instructor",
                     email="rollback-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="rollback-program", title="Program",
                                  slug="rollback-program"),
                CurriculumCourse(course_id="rollback-course",
                                 program_id="rollback-program", title="Course",
                                 slug="rollback-course"),
                CurriculumUnit(unit_id="rollback-unit", course_id="rollback-course",
                               title="Unit"),
                CurriculumLesson(lesson_id="rollback-lesson", unit_id="rollback-unit",
                                 title="Lesson", status="DRAFT"),
                TeachingMaterial(material_id="rollback-material",
                                 lesson_id="rollback-lesson",
                                 created_by_user_id="rollback-instructor",
                                 title="Rollback material"),
                TeachingMaterialVersion(version_id="rollback-version",
                    material_id="rollback-material", version=1,
                    submitted_by_user_id="rollback-instructor",
                    storage_key="synthetic/rollback/v1", sha256_hex="b" * 64,
                    byte_size=12, media_type="application/pdf", approved=False),
            ])
            db.commit()
            result = owner_approve_teaching_material_version(
                db, actor_user_id="rollback-owner", version_id="rollback-version"
            )
            assert result["approved"] is True
            assert db.query(AuditEvent).filter_by(
                action="teaching_material.version.approve",
                resource_id="rollback-version",
            ).count() == 1
            db.rollback()
        with Session(engine) as verify:
            version = verify.get(TeachingMaterialVersion, "rollback-version")
            assert version.approved is False
            assert version.approved_by_user_id is None
            assert verify.query(AuditEvent).filter_by(
                action="teaching_material.version.approve",
                resource_id="rollback-version",
            ).count() == 0
    finally:
        engine.dispose()
