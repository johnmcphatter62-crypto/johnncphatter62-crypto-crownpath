"""Actual CrownPath HTTP classroom continuity with AI provider unavailable.

Disposable SQLite and synthetic account only. No live AI/provider calls.
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_real_classroom_http_routes_work_with_ai_disabled(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'offline_http.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-offline-http-test-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="offline-learner", name="Offline Learner",
                        email="offline-learner@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            assert client.get("/api/learner/dashboard").status_code == 401
            login = client.post("/api/auth/login", json={
                "email": "offline-learner@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            dashboard = client.get("/api/learner/dashboard")
            assert dashboard.status_code == 200
            lesson_id = dashboard.json()["modules"][0]["lesson_id"]
            opened = client.post(f"/api/learner/lessons/{lesson_id}/open")
            assert opened.status_code == 200, opened.text
            completed = client.post(
                f"/api/learner/lessons/{lesson_id}/steps/1/complete")
            assert completed.status_code == 200, completed.text
            reopened = client.post(f"/api/learner/lessons/{lesson_id}/open")
            assert reopened.status_code == 200
            assert 1 in reopened.json()["lesson"]["completed_steps"]
            assert client.get("/api/owner/curriculum/progress-summary").status_code == 403
            assert client.post("/api/learner/lessons/barber-foundations/open").status_code == 404
    finally:
        engine.dispose()
