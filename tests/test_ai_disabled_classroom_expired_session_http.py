"""Expired persisted session must fail classroom HTTP routes during AI outage.

Disposable SQLite, synthetic user, no external AI or production access.
"""
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import AuthToken, User


def test_expired_session_denied_on_classroom_routes_when_ai_disabled(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'offline_expired.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-offline-expiry-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="offline-expired", name="Expired Learner",
                        email="offline-expired@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "offline-expired@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            assert client.get("/api/learner/dashboard").status_code == 200
            with Session(engine) as db:
                db.execute(update(AuthToken).where(
                    AuthToken.user_id == "offline-expired",
                    AuthToken.token_type == "SESSION"
                ).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
                db.commit()
            assert client.get("/api/learner/dashboard").status_code == 401
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/open"
            ).status_code == 401
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/steps/1/complete"
            ).status_code == 401
    finally:
        engine.dispose()
