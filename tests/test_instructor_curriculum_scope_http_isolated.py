"""Instructor curriculum editing stays blocked until assigned-scope controls exist."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_instructor_cannot_create_owner_curriculum_drafts(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'instructor_curriculum_scope.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-instructor-curriculum-key")
    monkeypatch.setattr(main, "role_access_approved", lambda role: True)
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-curriculum-instructor",
                name="Synthetic Curriculum Instructor",
                email="curriculum-instructor@example.com",
                password_hash=auth.hash_password(password),
                role="INSTRUCTOR", active=True, mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "curriculum-instructor@example.com",
                "password": password,
            })
            assert login.status_code == 200, login.text
            assert client.get("/api/academy").status_code == 200
            attempts = [
                client.post("/api/owner/curriculum/programs", json={
                    "title": "Synthetic Course", "slug": "synthetic-course",
                }),
                client.post("/api/owner/curriculum/courses", json={
                    "program_id": "synthetic-program",
                    "title": "Synthetic Course", "slug": "synthetic-course",
                }),
                client.post("/api/owner/curriculum/lessons", json={
                    "unit_id": "synthetic-unit", "title": "Synthetic Lesson",
                }),
                client.post("/api/owner/curriculum/lesson-versions", json={
                    "lesson_id": "synthetic-lesson",
                    "content_json": "{}", "version": 1,
                }),
            ]
            assert all(response.status_code == 403 for response in attempts), [
                (response.status_code, response.text) for response in attempts
            ]
    finally:
        engine.dispose()
