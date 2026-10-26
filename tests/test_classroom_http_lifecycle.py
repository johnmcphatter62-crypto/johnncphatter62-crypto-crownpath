"""HTTP classroom smoke test with disposable SQLite and synthetic auth."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_http_classroom_lifecycle(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'http_classroom.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "isolated-http-classroom-test-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        with Session(engine) as db:
            db.add(User(user_id="http-learner", name="HTTP Learner",
                        email="http-learner@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "http-learner@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            assert login.json()["authenticated"] is True
            dashboard = client.get("/api/learner/dashboard")
            assert dashboard.status_code == 200
            lesson_id = dashboard.json()["modules"][0]["lesson_id"]
            opened = client.post(f"/api/learner/lessons/{lesson_id}/open")
            assert opened.status_code == 200
            completed = client.post(
                f"/api/learner/lessons/{lesson_id}/steps/1/complete")
            assert completed.status_code == 200
            assert 1 in completed.json()["lesson"]["completed_steps"]
            reopened = client.post(f"/api/learner/lessons/{lesson_id}/open")
            assert reopened.status_code == 200
            assert 1 in reopened.json()["lesson"]["completed_steps"]
            forbidden = client.post("/api/learner/lessons/barber-foundations/open")
            assert forbidden.status_code == 404
    finally:
        engine.dispose()
