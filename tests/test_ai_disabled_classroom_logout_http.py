"""CrownPath actual HTTP logout revokes prior session during AI outage.

Disposable SQLite and fictional learner only.
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_logout_revokes_reused_session_cookie_with_ai_disabled(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'offline_logout.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-offline-logout-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="offline-logout", name="Logout Learner",
                        email="offline-logout@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "offline-logout@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            old_cookie = client.cookies.get("crownpath_session")
            assert old_cookie
            assert client.get("/api/learner/dashboard").status_code == 200
            logout = client.post("/api/auth/logout")
            assert logout.status_code == 200, logout.text
            assert client.get("/api/learner/dashboard").status_code == 401
            # A copied cookie must not restore a revoked server-side session.
            client.cookies.set("crownpath_session", old_cookie)
            assert client.get("/api/learner/dashboard").status_code == 401
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/open"
            ).status_code == 401
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/steps/1/complete"
            ).status_code == 401
    finally:
        engine.dispose()
