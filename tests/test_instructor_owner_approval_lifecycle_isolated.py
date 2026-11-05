"""Synthetic instructor-to-Owner lesson approval lifecycle in disposable SQLite."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crownpath.curriculum_models import (
    CurriculumCourse, CurriculumLesson, CurriculumLessonVersion,
    CurriculumProgram, CurriculumUnit,
)
from crownpath.db_engine import Base
from crownpath.instructor_assignments import set_course_assignment_active
from crownpath.instructor_drafts import create_instructor_unapproved_draft
from crownpath.models import AuditEvent, InstructorCourseAssignment, User
from crownpath.owner_curriculum import approve_lesson_version


def test_instructor_to_owner_approval_and_audit(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'approval_lifecycle.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Synthetic Owner", email="lifecycle-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Synthetic Instructor",
                     email="lifecycle-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Synthetic Program", slug="lifecycle-program"),
                CurriculumCourse(course_id="course", program_id="program", title="Course", slug="course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit", title="Draft", status="DRAFT"),
                InstructorCourseAssignment(assignment_id="assignment", instructor_user_id="instructor",
                                           course_id="course", assigned_by_user_id="owner"),
            ])
            db.commit()
            set_course_assignment_active(db, actor_user_id="owner", assignment_id="assignment", active=True)
            db.commit()

            draft = create_instructor_unapproved_draft(
                db, instructor_user_id="instructor", lesson_id="lesson",
                content_json='{"synthetic":true}', version=2,
            )
            db.commit()
            assert draft["approved"] is False
            with pytest.raises(PermissionError):
                approve_lesson_version(
                    db, {"user_id": "instructor", "role": "INSTRUCTOR", "active": True},
                    version_id=draft["version_id"],
                )
            assert db.get(CurriculumLessonVersion, draft["version_id"]).approved is False
            approved = approve_lesson_version(
                db, {"user_id": "owner", "role": "OWNER", "active": True},
                version_id=draft["version_id"],
            )
            assert approved["approved"] is True
            assert approved["approved_by"] == "owner"
            assert approved["approved_at"] is not None
            assert approved["lesson_status"] == "DRAFT"
            assert db.get(CurriculumLesson, "lesson").active_version == 2
            event = db.scalar(select(AuditEvent).where(
                AuditEvent.action == "CURRICULUM_LESSON_VERSION_APPROVED",
                AuditEvent.resource_id == draft["version_id"],
            ))
            assert event is not None
            assert event.user_id == "owner"
            assert event.result == "SUCCESS"
            with pytest.raises(ValueError, match="already approved"):
                approve_lesson_version(
                    db, {"user_id": "owner", "role": "OWNER", "active": True},
                    version_id=draft["version_id"],
                )
    finally:
        engine.dispose()
