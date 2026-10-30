"""Owner-only material approval tests using synthetic disposable SQLite."""
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy.exc import OperationalError
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
            assert events[0].category == "curriculum"
            assert events[0].resource_type == "teaching_material_version"
            assert events[0].resource_id == "version"
            assert events[0].reason == "Explicit Owner approval of unapproved material metadata"
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


def test_approval_retry_after_rollback_creates_only_one_success_event(tmp_path):
    """A rolled-back attempt may be retried without duplicate audit success."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'approval_retry.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="retry-owner", name="Owner",
                     email="retry-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="retry-instructor", name="Instructor",
                     email="retry-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="retry-program", title="Program",
                                  slug="retry-program"),
                CurriculumCourse(course_id="retry-course",
                                 program_id="retry-program", title="Course",
                                 slug="retry-course"),
                CurriculumUnit(unit_id="retry-unit", course_id="retry-course",
                               title="Unit"),
                CurriculumLesson(lesson_id="retry-lesson", unit_id="retry-unit",
                                 title="Lesson", status="DRAFT"),
                TeachingMaterial(material_id="retry-material",
                                 lesson_id="retry-lesson",
                                 created_by_user_id="retry-instructor",
                                 title="Retry material"),
                TeachingMaterialVersion(version_id="retry-version",
                    material_id="retry-material", version=1,
                    submitted_by_user_id="retry-instructor",
                    storage_key="synthetic/retry/v1", sha256_hex="c" * 64,
                    byte_size=12, media_type="application/pdf", approved=False),
            ])
            db.commit()
            owner_approve_teaching_material_version(
                db, actor_user_id="retry-owner", version_id="retry-version"
            )
            db.rollback()
            result = owner_approve_teaching_material_version(
                db, actor_user_id="retry-owner", version_id="retry-version"
            )
            assert result["approved"] is True
            db.commit()
            with pytest.raises(ValueError):
                owner_approve_teaching_material_version(
                    db, actor_user_id="retry-owner", version_id="retry-version"
                )
        with Session(engine) as verify:
            assert verify.get(TeachingMaterialVersion, "retry-version").approved is True
            events = verify.query(AuditEvent).filter_by(
                action="teaching_material.version.approve",
                resource_id="retry-version", result="SUCCESS",
            ).all()
            assert len(events) == 1
            assert events[0].user_id == "retry-owner"
    finally:
        engine.dispose()


def test_two_sessions_cannot_both_approve_same_version(tmp_path):
    """Sequential competing sessions must produce only one successful audit."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'competing_approval.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as setup:
            setup.add_all([
                User(user_id="compete-owner", name="Owner",
                     email="compete-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="compete-instructor", name="Instructor",
                     email="compete-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="compete-program", title="Program",
                                  slug="compete-program"),
                CurriculumCourse(course_id="compete-course",
                                 program_id="compete-program", title="Course",
                                 slug="compete-course"),
                CurriculumUnit(unit_id="compete-unit", course_id="compete-course",
                               title="Unit"),
                CurriculumLesson(lesson_id="compete-lesson", unit_id="compete-unit",
                                 title="Lesson", status="DRAFT"),
                TeachingMaterial(material_id="compete-material",
                                 lesson_id="compete-lesson",
                                 created_by_user_id="compete-instructor",
                                 title="Competing material"),
                TeachingMaterialVersion(version_id="compete-version",
                    material_id="compete-material", version=1,
                    submitted_by_user_id="compete-instructor",
                    storage_key="synthetic/compete/v1", sha256_hex="d" * 64,
                    byte_size=12, media_type="application/pdf", approved=False),
            ])
            setup.commit()
        with Session(engine) as first, Session(engine) as second:
            # Both sessions initially observe the same unapproved version.
            assert first.get(TeachingMaterialVersion, "compete-version").approved is False
            assert second.get(TeachingMaterialVersion, "compete-version").approved is False
            owner_approve_teaching_material_version(
                first, actor_user_id="compete-owner", version_id="compete-version"
            )
            first.commit()
            with pytest.raises(ValueError):
                owner_approve_teaching_material_version(
                    second, actor_user_id="compete-owner", version_id="compete-version"
                )
            second.rollback()
        with Session(engine) as verify:
            record = verify.get(TeachingMaterialVersion, "compete-version")
            assert record.approved is True
            assert record.approved_by_user_id == "compete-owner"
            events = verify.query(AuditEvent).filter_by(
                action="teaching_material.version.approve",
                resource_id="compete-version", result="SUCCESS",
            ).all()
            assert len(events) == 1
    finally:
        engine.dispose()


def test_parallel_owner_approval_never_commits_two_success_events(tmp_path):
    """Concurrent SQLite requests may contend, but never double-approve."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'parallel_approval.db'}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as setup:
            setup.add_all([
                User(user_id="parallel-owner", name="Owner",
                     email="parallel-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="parallel-instructor", name="Instructor",
                     email="parallel-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="parallel-program", title="Program",
                                  slug="parallel-program"),
                CurriculumCourse(course_id="parallel-course",
                                 program_id="parallel-program", title="Course",
                                 slug="parallel-course"),
                CurriculumUnit(unit_id="parallel-unit", course_id="parallel-course",
                               title="Unit"),
                CurriculumLesson(lesson_id="parallel-lesson", unit_id="parallel-unit",
                                 title="Lesson", status="DRAFT"),
                TeachingMaterial(material_id="parallel-material",
                                 lesson_id="parallel-lesson",
                                 created_by_user_id="parallel-instructor",
                                 title="Parallel material"),
                TeachingMaterialVersion(version_id="parallel-version",
                    material_id="parallel-material", version=1,
                    submitted_by_user_id="parallel-instructor",
                    storage_key="synthetic/parallel/v1", sha256_hex="e" * 64,
                    byte_size=12, media_type="application/pdf", approved=False),
            ])
            setup.commit()

        gate = Barrier(2)

        def attempt():
            with Session(engine) as db:
                gate.wait(timeout=10)
                try:
                    owner_approve_teaching_material_version(
                        db, actor_user_id="parallel-owner",
                        version_id="parallel-version"
                    )
                    db.commit()
                    return "approved"
                except (ValueError, OperationalError):
                    db.rollback()
                    return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        assert results.count("approved") == 1
        assert results.count("rejected") == 1
        with Session(engine) as verify:
            record = verify.get(TeachingMaterialVersion, "parallel-version")
            assert record.approved is True
            assert record.approved_by_user_id == "parallel-owner"
            events = verify.query(AuditEvent).filter_by(
                action="teaching_material.version.approve",
                resource_id="parallel-version", result="SUCCESS",
            ).all()
            assert len(events) == 1
    finally:
        engine.dispose()
