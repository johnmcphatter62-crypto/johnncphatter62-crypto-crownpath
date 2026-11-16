"""Shared-lesson authorization is enforced at draft-write time."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.curriculum_models import (
    CurriculumCourse, CurriculumLesson, CurriculumLessonVersion,
    CurriculumProgram, CurriculumUnit, CurriculumUnitLesson,
)
from crownpath.db_engine import Base
from crownpath.instructor_assignments import set_course_assignment_active
from crownpath.instructor_drafts import create_instructor_unapproved_draft
from crownpath.models import InstructorCourseAssignment, User


def test_shared_lesson_draft_write_denied_without_every_assignment(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'shared_draft_write.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Synthetic Owner",
                     email="shared-write-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="instructor", name="Synthetic Instructor",
                     email="shared-write-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Synthetic Program",
                                  slug="shared-write-program"),
                CurriculumCourse(course_id="course-a", program_id="program",
                                 title="Course A", slug="course-a"),
                CurriculumCourse(course_id="course-b", program_id="program",
                                 title="Course B", slug="course-b"),
                CurriculumUnit(unit_id="unit-a", course_id="course-a", title="Unit A"),
                CurriculumUnit(unit_id="unit-b", course_id="course-b", title="Unit B"),
                CurriculumLesson(lesson_id="shared", unit_id="unit-a",
                                 title="Shared Draft", status="DRAFT"),
                CurriculumUnitLesson(assignment_id="placement-b", unit_id="unit-b",
                                     lesson_id="shared"),
                InstructorCourseAssignment(
                    assignment_id="assignment-a", instructor_user_id="instructor",
                    course_id="course-a", assigned_by_user_id="owner"),
                InstructorCourseAssignment(
                    assignment_id="assignment-b", instructor_user_id="instructor",
                    course_id="course-b", assigned_by_user_id="owner"),
            ])
            db.commit()
            set_course_assignment_active(db, actor_user_id="owner",
                                         assignment_id="assignment-a", active=True)
            db.commit()
            with pytest.raises(PermissionError):
                create_instructor_unapproved_draft(
                    db, instructor_user_id="instructor", lesson_id="shared",
                    content_json='{"synthetic":true}', version=2,
                )
            assert db.query(CurriculumLessonVersion).count() == 0
            set_course_assignment_active(db, actor_user_id="owner",
                                         assignment_id="assignment-b", active=True)
            db.commit()
            draft = create_instructor_unapproved_draft(
                db, instructor_user_id="instructor", lesson_id="shared",
                content_json='{"synthetic":true}', version=2,
            )
            db.commit()
            assert draft["approved"] is False
            assert db.query(CurriculumLessonVersion).count() == 1
            set_course_assignment_active(db, actor_user_id="owner",
                                         assignment_id="assignment-b", active=False)
            db.commit()
            with pytest.raises(PermissionError):
                create_instructor_unapproved_draft(
                    db, instructor_user_id="instructor", lesson_id="shared",
                    content_json='{"synthetic":true}', version=3,
                )
            assert db.query(CurriculumLessonVersion).count() == 1
    finally:
        engine.dispose()
