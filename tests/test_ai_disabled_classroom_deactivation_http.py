"""Actual CrownPath HTTP learner deactivation during AI outage.

Disposable SQLite and fictional account. No live data, AI calls or deployment.
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_deactivated_learner_loses_existing_session_during_ai_outage(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'offline_deactivation.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-offline-deactivation-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="offline-revoked", name="Offline Revoked Learner",
                        email="offline-revoked@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "offline-revoked@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            assert client.get("/api/learner/dashboard").status_code == 200
            with Session(engine) as db:
                learner = db.query(User).filter_by(user_id="offline-revoked").one()
                learner.active = False
                db.commit()
            assert client.get("/api/learner/dashboard").status_code == 401
            assert client.post("/api/learner/lessons/cosmetology-foundations/open").status_code == 401
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/steps/1/complete"
            ).status_code == 401
    finally:
        engine.dispose()
