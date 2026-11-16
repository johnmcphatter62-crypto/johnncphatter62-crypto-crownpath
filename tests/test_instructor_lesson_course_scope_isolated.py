"""Lesson authorization resolves the actual course from disposable SQLite."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.curriculum_models import CurriculumCourse, CurriculumLesson, CurriculumProgram, CurriculumUnit
from crownpath.db_engine import Base
from crownpath.instructor_assignments import instructor_can_edit_lesson, set_course_assignment_active
from crownpath.models import InstructorCourseAssignment, User


def test_lesson_authorization_follows_actual_parent_course(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'lesson_course_scope.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Synthetic Owner",
                     email="lesson-owner@example.com", password_hash="synthetic",
                     role="OWNER", active=True),
                User(user_id="instructor", name="Synthetic Instructor",
                     email="lesson-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Synthetic Program", slug="synthetic-program"),
                CurriculumCourse(course_id="course-a", program_id="program", title="Course A", slug="course-a"),
                CurriculumCourse(course_id="course-b", program_id="program", title="Course B", slug="course-b"),
                CurriculumUnit(unit_id="unit-a", course_id="course-a", title="Unit A"),
                CurriculumUnit(unit_id="unit-b", course_id="course-b", title="Unit B"),
                CurriculumLesson(lesson_id="lesson-a", unit_id="unit-a", title="Draft A", status="DRAFT"),
                CurriculumLesson(lesson_id="lesson-b", unit_id="unit-b", title="Draft B", status="DRAFT"),
                CurriculumLesson(lesson_id="published", unit_id="unit-a", title="Published", status="PUBLISHED"),
                InstructorCourseAssignment(
                    assignment_id="assignment", instructor_user_id="instructor",
                    course_id="course-a", assigned_by_user_id="owner",
                ),
            ])
            db.commit()
            assert not instructor_can_edit_lesson(db, instructor_user_id="instructor", lesson_id="lesson-a")
            set_course_assignment_active(db, actor_user_id="owner", assignment_id="assignment", active=True)
            db.commit()
            assert instructor_can_edit_lesson(db, instructor_user_id="instructor", lesson_id="lesson-a")
            assert not instructor_can_edit_lesson(db, instructor_user_id="instructor", lesson_id="lesson-b")
            assert not instructor_can_edit_lesson(db, instructor_user_id="instructor", lesson_id="published")
            assert not instructor_can_edit_lesson(db, instructor_user_id="instructor", lesson_id="missing")
            set_course_assignment_active(db, actor_user_id="owner", assignment_id="assignment", active=False)
            db.commit()
            assert not instructor_can_edit_lesson(db, instructor_user_id="instructor", lesson_id="lesson-a")
    finally:
        engine.dispose()
