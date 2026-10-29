"""Synthetic assigned-instructor draft creation is unapproved and course-scoped."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crownpath.curriculum_models import (
    CurriculumCourse, CurriculumLesson, CurriculumLessonVersion, CurriculumProgram, CurriculumUnit,
)
from crownpath.db_engine import Base
from crownpath.instructor_assignments import set_course_assignment_active
from crownpath.instructor_drafts import create_instructor_unapproved_draft
from crownpath.models import InstructorCourseAssignment, User


def test_instructor_draft_is_unapproved_and_unassigned_course_denied(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'instructor_draft.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Synthetic Owner",
                     email="draft-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="instructor", name="Synthetic Instructor",
                     email="draft-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Synthetic Program", slug="draft-program"),
                CurriculumCourse(course_id="course-a", program_id="program", title="Course A", slug="course-a"),
                CurriculumCourse(course_id="course-b", program_id="program", title="Course B", slug="course-b"),
                CurriculumUnit(unit_id="unit-a", course_id="course-a", title="Unit A"),
                CurriculumUnit(unit_id="unit-b", course_id="course-b", title="Unit B"),
                CurriculumLesson(lesson_id="lesson-a", unit_id="unit-a", title="Draft A", status="DRAFT"),
                CurriculumLesson(lesson_id="lesson-b", unit_id="unit-b", title="Draft B", status="DRAFT"),
                InstructorCourseAssignment(
                    assignment_id="assignment", instructor_user_id="instructor",
                    course_id="course-a", assigned_by_user_id="owner",
                ),
            ])
            db.commit()
            set_course_assignment_active(db, actor_user_id="owner", assignment_id="assignment", active=True)
            db.commit()

            created = create_instructor_unapproved_draft(
                db, instructor_user_id="instructor", lesson_id="lesson-a",
                content_json='{"synthetic":true}', version=2,
            )
            db.commit()
            assert created["approved"] is False
            saved = db.scalar(select(CurriculumLessonVersion).where(
                CurriculumLessonVersion.lesson_id == "lesson-a",
                CurriculumLessonVersion.version == 2,
            ))
            assert saved is not None
            assert saved.approved is False
            assert saved.approved_by is None
            assert saved.approved_at is None

            with pytest.raises(PermissionError):
                create_instructor_unapproved_draft(
                    db, instructor_user_id="instructor", lesson_id="lesson-b",
                    content_json='{"synthetic":true}', version=2,
                )
            with pytest.raises(ValueError, match="already exists"):
                create_instructor_unapproved_draft(
                    db, instructor_user_id="instructor", lesson_id="lesson-a",
                    content_json='{"synthetic":true}', version=2,
                )
            db.commit()
            assert db.query(CurriculumLessonVersion).count() == 1

            set_course_assignment_active(db, actor_user_id="owner", assignment_id="assignment", active=False)
            db.commit()
            with pytest.raises(PermissionError):
                create_instructor_unapproved_draft(
                    db, instructor_user_id="instructor", lesson_id="lesson-a",
                    content_json='{"synthetic":true}', version=3,
                )
            assert db.query(CurriculumLessonVersion).count() == 1
    finally:
        engine.dispose()
