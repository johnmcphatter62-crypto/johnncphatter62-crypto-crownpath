"""HTTP route security tests with synthetic identity and disposable SQLite."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath import main
from crownpath.curriculum_models import (
    CurriculumCourse, CurriculumLesson, CurriculumLessonVersion,
    CurriculumProgram, CurriculumUnit,
)
from crownpath.db_engine import Base
from crownpath.models import InstructorCourseAssignment, User


def test_instructor_http_route_permissions_and_origin(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'http_instructor.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    identity = {"user_id": "instructor", "role": "INSTRUCTOR", "active": True}
    try:
        with Session(engine) as db:
            db.add_all([
                User(user_id="owner", name="Owner", email="http-owner@example.com",
                     password_hash="synthetic", role="OWNER", active=True),
                User(user_id="instructor", name="Instructor",
                     email="http-instructor@example.com", password_hash="synthetic",
                     role="INSTRUCTOR", active=True),
                CurriculumProgram(program_id="program", title="Program", slug="http-program"),
                CurriculumCourse(course_id="course", program_id="program",
                                 title="Course", slug="http-course"),
                CurriculumUnit(unit_id="unit", course_id="course", title="Unit"),
                CurriculumLesson(lesson_id="lesson", unit_id="unit",
                                 title="Lesson", status="DRAFT"),
                InstructorCourseAssignment(assignment_id="assignment",
                    instructor_user_id="instructor", course_id="course",
                    assigned_by_user_id="owner", active=True),
            ])
            db.commit()
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        main.app.dependency_overrides[main.current_user] = lambda: identity
        payload = {"lesson_id": "lesson", "content_json": '{"text":"Draft"}', "version": 2}
        with TestClient(main.app, base_url="https://testserver") as client:
            # Middleware checks Origin when the session cookie is present.
            client.cookies.set("crownpath_session", "synthetic")
            url = "/api/instructor/curriculum/drafts"
            assert client.post(url, json=payload).status_code == 403
            assert client.post(url, json=payload,
                headers={"Origin": "https://attacker.example"}).status_code == 403
            identity.update(user_id="owner", role="OWNER")
            assert client.post(url, json=payload,
                headers={"Origin": "https://testserver"}).status_code == 403
            identity.update(user_id="instructor", role="INSTRUCTOR")
            ok = client.post(url, json=payload,
                             headers={"Origin": "https://testserver"})
            assert ok.status_code == 200, ok.text
            assert ok.json()["approved"] is False
            with Session(engine) as db:
                item = db.get(CurriculumLessonVersion, ok.json()["version_id"])
                assert item.approved is False and item.approved_by is None
                db.get(InstructorCourseAssignment, "assignment").active = False
                db.commit()
            denied = client.post(url, json={**payload, "version": 3},
                                 headers={"Origin": "https://testserver"})
            assert denied.status_code == 403
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
