"""Isolated instructor HTTP handler permission tests, no live service."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath import main
from crownpath.curriculum_models import (
    CurriculumCourse, CurriculumLesson, CurriculumLessonVersion,
    CurriculumProgram, CurriculumUnit,
)
from crownpath.db_engine import Base
from crownpath.models import InstructorCourseAssignment, User


def test_instructor_draft_endpoint_assignment_and_role(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'endpoint_security.db'}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Synthetic Owner", email="owner-endpoint@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Synthetic Instructor",
                     email="instructor-endpoint@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Program", slug="endpoint-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="endpoint-course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit", title="Lesson",
                                 status="DRAFT"),
                InstructorCourseAssignment(assignment_id="assignment",
                    instructor_user_id="instructor", course_id="course",
                    assigned_by_user_id="owner", active=False),
            ])
            db.commit()
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        payload = main.InstructorDraftSubmitRequest(
            lesson_id="lesson", content_json='{"text":"Draft"}', version=2
        )
        instructor = {"user_id": "instructor", "role": "INSTRUCTOR", "active": True}
        with pytest.raises(HTTPException) as denied:
            main.instructor_submit_draft(payload, user=instructor)
        assert denied.value.status_code == 403

        with Session(engine) as db:
            db.get(InstructorCourseAssignment, "assignment").active = True
            db.commit()
        with pytest.raises(HTTPException) as owner_denied:
            main.instructor_submit_draft(payload, user={
                "user_id": "owner", "role": "OWNER", "active": True
            })
        assert owner_denied.value.status_code == 403

        result = main.instructor_submit_draft(payload, user=instructor)
        assert result["approved"] is False
        with Session(engine) as db:
            item = db.get(CurriculumLessonVersion, result["version_id"])
            assert item is not None and item.approved is False
            assert item.approved_by is None
            db.get(InstructorCourseAssignment, "assignment").active = False
            db.commit()
        with pytest.raises(HTTPException) as revoked:
            main.instructor_submit_draft(
                main.InstructorDraftSubmitRequest(
                    lesson_id="lesson", content_json='{"text":"Second"}', version=3
                ), user=instructor,
            )
        assert revoked.value.status_code == 403
        with Session(engine) as db:
            assert db.query(CurriculumLessonVersion).count() == 1
    finally:
        engine.dispose()
