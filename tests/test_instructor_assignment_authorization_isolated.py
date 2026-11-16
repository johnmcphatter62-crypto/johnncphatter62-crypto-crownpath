"""Owner-only assignment activation and revocation using disposable SQLite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.instructor_assignments import set_course_assignment_active
from crownpath.models import InstructorCourseAssignment, User


def test_owner_only_activation_revocation_and_disabled_instructor(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'assignment_access.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(
                    user_id="owner", name="Synthetic Owner",
                    email="assignment-actor-owner@example.com",
                    password_hash="synthetic-only", role="OWNER", active=True,
                ),
                User(
                    user_id="instructor", name="Synthetic Instructor",
                    email="assignment-actor-instructor@example.com",
                    password_hash="synthetic-only", role="INSTRUCTOR", active=True,
                ),
                User(
                    user_id="learner", name="Synthetic Learner",
                    email="assignment-actor-learner@example.com",
                    password_hash="synthetic-only", role="BARBER", active=True,
                ),
            ])
            db.add(InstructorCourseAssignment(
                assignment_id="assignment-one", instructor_user_id="instructor",
                course_id="synthetic-course", assigned_by_user_id="owner",
            ))
            db.commit()

            with pytest.raises(PermissionError):
                set_course_assignment_active(
                    db, actor_user_id="learner", assignment_id="assignment-one", active=True
                )
            assert db.get(InstructorCourseAssignment, "assignment-one").active is False

            activated = set_course_assignment_active(
                db, actor_user_id="owner", assignment_id="assignment-one", active=True
            )
            assert activated.active is True
            db.commit()

            revoked = set_course_assignment_active(
                db, actor_user_id="owner", assignment_id="assignment-one", active=False
            )
            assert revoked.active is False
            db.commit()

            db.get(User, "instructor").active = False
            db.commit()
            with pytest.raises(ValueError, match="Active instructor"):
                set_course_assignment_active(
                    db, actor_user_id="owner", assignment_id="assignment-one", active=True
                )
            assert db.get(InstructorCourseAssignment, "assignment-one").active is False

            db.get(User, "owner").active = False
            db.commit()
            with pytest.raises(PermissionError):
                set_course_assignment_active(
                    db, actor_user_id="owner", assignment_id="assignment-one", active=False
                )
    finally:
        engine.dispose()
