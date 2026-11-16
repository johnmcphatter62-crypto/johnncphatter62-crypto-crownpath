"""Disabled instructors and invalid content cannot create lesson drafts."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.curriculum_models import (
    CurriculumCourse, CurriculumLesson, CurriculumLessonVersion,
    CurriculumProgram, CurriculumUnit,
)
from crownpath.db_engine import Base
from crownpath.instructor_assignments import set_course_assignment_active
from crownpath.instructor_drafts import create_instructor_unapproved_draft
from crownpath.models import InstructorCourseAssignment, User


def test_disabled_instructor_and_invalid_content_fail_closed(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'draft_validation.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Synthetic Owner",
                     email="validation-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="instructor", name="Synthetic Instructor",
                     email="validation-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Synthetic Program",
                                  slug="validation-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit",
                                 title="Draft", status="DRAFT"),
                InstructorCourseAssignment(assignment_id="assignment",
                                           instructor_user_id="instructor",
                                           course_id="course", assigned_by_user_id="owner"),
            ])
            db.commit()
            set_course_assignment_active(db, actor_user_id="owner",
                                         assignment_id="assignment", active=True)
            db.commit()
            for payload, version in [("", 2), ("   ", 2), ('{"synthetic":true}', 0)]:
                with pytest.raises(ValueError):
                    create_instructor_unapproved_draft(
                        db, instructor_user_id="instructor", lesson_id="lesson",
                        content_json=payload, version=version,
                    )
            assert db.query(CurriculumLessonVersion).count() == 0
            instructor = db.get(User, "instructor")
            instructor.active = False
            db.commit()
            with pytest.raises(PermissionError):
                create_instructor_unapproved_draft(
                    db, instructor_user_id="instructor", lesson_id="lesson",
                    content_json='{"synthetic":true}', version=2,
                )
            assert db.query(CurriculumLessonVersion).count() == 0
    finally:
        engine.dispose()
