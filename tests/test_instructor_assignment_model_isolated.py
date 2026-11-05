"""Disposable SQLite checks for fail-closed instructor course assignment records."""
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import InstructorCourseAssignment, User


def test_course_assignments_default_inactive_and_reject_duplicates(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'instructor_assignments.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(
                    user_id="synthetic-owner", name="Synthetic Owner",
                    email="assignment-owner@example.com", password_hash="synthetic-only",
                    role="OWNER", active=True,
                ),
                User(
                    user_id="synthetic-instructor", name="Synthetic Instructor",
                    email="assignment-instructor@example.com", password_hash="synthetic-only",
                    role="INSTRUCTOR", active=True,
                ),
            ])
            db.commit()
            assignment = InstructorCourseAssignment(
                assignment_id=str(uuid4()),
                instructor_user_id="synthetic-instructor",
                course_id="synthetic-course-one",
                assigned_by_user_id="synthetic-owner",
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            assert assignment.active is False
            assert assignment.assigned_by_user_id == "synthetic-owner"

            duplicate = InstructorCourseAssignment(
                assignment_id=str(uuid4()),
                instructor_user_id="synthetic-instructor",
                course_id="synthetic-course-one",
                assigned_by_user_id="synthetic-owner",
            )
            db.add(duplicate)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
            existing = db.query(InstructorCourseAssignment).all()
            assert len(existing) == 1
            assert existing[0].active is False
    finally:
        engine.dispose()
