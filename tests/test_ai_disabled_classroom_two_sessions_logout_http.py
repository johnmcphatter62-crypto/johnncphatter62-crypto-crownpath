"""Logout revokes only its own session, not another valid learner session.

Actual CrownPath HTTP routes; synthetic user and disposable SQLite only.
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_logout_is_scoped_to_one_session_with_ai_disabled(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'offline_two_sessions.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-two-sessions-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="offline-two-sessions", name="Two Session Learner",
                        email="offline-two-sessions@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as first, \
             TestClient(main.app, headers={"Origin": "http://testserver"}) as second:
            credentials = {"email": "offline-two-sessions@example.com",
                           "password": "SyntheticPassword!2026"}
            assert first.post("/api/auth/login", json=credentials).status_code == 200
            assert second.post("/api/auth/login", json=credentials).status_code == 200
            first_cookie = first.cookies.get("crownpath_session")
            second_cookie = second.cookies.get("crownpath_session")
            assert first_cookie and second_cookie and first_cookie != second_cookie
            assert first.get("/api/learner/dashboard").status_code == 200
            assert second.get("/api/learner/dashboard").status_code == 200
            assert first.post("/api/auth/logout").status_code == 200
            assert first.get("/api/learner/dashboard").status_code == 401
            first.cookies.set("crownpath_session", first_cookie)
            assert first.get("/api/learner/dashboard").status_code == 401
            assert second.get("/api/learner/dashboard").status_code == 200
            assert second.post(
                "/api/learner/lessons/cosmetology-foundations/open"
            ).status_code == 200
    finally:
        engine.dispose()
