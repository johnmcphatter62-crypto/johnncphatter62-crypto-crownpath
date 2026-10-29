"""Isolated authorization tests for official teaching materials."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, InstructorCourseAssignment
from crownpath.curriculum_models import (
    CurriculumProgram, CurriculumCourse, CurriculumUnit, CurriculumLesson,
)
from crownpath.teaching_material_models import TeachingMaterial
from crownpath.teaching_material_permissions import (
    can_submit_teaching_material_version, can_owner_review_teaching_material,
)


def test_owner_and_instructor_material_access_is_fail_closed(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'material_permissions.db'}",
        connect_args={"check_same_thread": False},
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Owner", email="material-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Instructor",
                     email="material-instructor@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                User(user_id="other", name="Other", email="material-other@example.com",
                     password_hash="synthetic", role="INSTRUCTOR", active=True),
                User(user_id="learner", name="Learner", email="material-learner@example.com",
                     password_hash="synthetic", role="HOME_CARE", active=True),
                CurriculumProgram(program_id="program", title="Program", slug="material-permission-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="material-permission-course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit",
                                 title="Lesson", status="DRAFT"),
                InstructorCourseAssignment(
                    assignment_id="assignment", instructor_user_id="instructor",
                    course_id="course", assigned_by_user_id="owner", active=True,
                ),
                TeachingMaterial(
                    material_id="material", lesson_id="lesson",
                    created_by_user_id="instructor", title="Official lesson file",
                ),
            ])
            db.commit()

            submit = lambda user: can_submit_teaching_material_version(
                db, actor_user_id=user, material_id="material"
            )
            review = lambda user: can_owner_review_teaching_material(
                db, actor_user_id=user, material_id="material"
            )
            assert submit("instructor") is True
            assert submit("owner") is False
            assert submit("other") is False
            assert submit("learner") is False
            assert submit("missing") is False
            assert review("owner") is True
            assert review("instructor") is False
            assert review("learner") is False
            assert can_owner_review_teaching_material(
                db, actor_user_id="owner", material_id="missing"
            ) is False

            db.get(InstructorCourseAssignment, "assignment").active = False
            db.flush()
            assert submit("instructor") is False

            db.get(InstructorCourseAssignment, "assignment").active = True
            db.get(User, "instructor").active = False
            db.flush()
            assert submit("instructor") is False

            db.get(User, "owner").active = False
            db.flush()
            assert review("owner") is False
    finally:
        engine.dispose()
