"""Assignment authorization is scoped to a course and revocable."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.instructor_assignments import instructor_can_edit_course, set_course_assignment_active
from crownpath.models import InstructorCourseAssignment, User


def test_assignment_scoped_to_course_and_revoked_immediately(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'course_scope.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(
                    user_id="owner", name="Synthetic Owner",
                    email="course-scope-owner@example.com", password_hash="synthetic",
                    role="OWNER", active=True,
                ),
                User(
                    user_id="instructor", name="Synthetic Instructor",
                    email="course-scope-instructor@example.com", password_hash="synthetic",
                    role="INSTRUCTOR", active=True,
                ),
                User(
                    user_id="other", name="Synthetic Other Instructor",
                    email="course-scope-other@example.com", password_hash="synthetic",
                    role="INSTRUCTOR", active=True,
                ),
            ])
            db.add(InstructorCourseAssignment(
                assignment_id="assignment", instructor_user_id="instructor",
                course_id="course-a", assigned_by_user_id="owner",
            ))
            db.commit()

            assert not instructor_can_edit_course(
                db, instructor_user_id="instructor", course_id="course-a"
            )
            set_course_assignment_active(
                db, actor_user_id="owner", assignment_id="assignment", active=True
            )
            db.commit()
            assert instructor_can_edit_course(
                db, instructor_user_id="instructor", course_id="course-a"
            )
            assert not instructor_can_edit_course(
                db, instructor_user_id="instructor", course_id="course-b"
            )
            assert not instructor_can_edit_course(
                db, instructor_user_id="other", course_id="course-a"
            )

            set_course_assignment_active(
                db, actor_user_id="owner", assignment_id="assignment", active=False
            )
            db.commit()
            assert not instructor_can_edit_course(
                db, instructor_user_id="instructor", course_id="course-a"
            )
            db.get(User, "instructor").active = False
            db.commit()
            assert not instructor_can_edit_course(
                db, instructor_user_id="instructor", course_id="course-a"
            )
    finally:
        engine.dispose()
