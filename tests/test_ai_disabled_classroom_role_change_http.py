"""Actual CrownPath classroom HTTP role-change test during AI outage.

Synthetic learner and disposable SQLite only; no production changes.
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_existing_session_cannot_keep_old_learner_path_after_role_change(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'offline_role_change.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-offline-role-change-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="offline-role-learner", name="Offline Role Learner",
                        email="offline-role-learner@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "offline-role-learner@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/open"
            ).status_code == 200
            with Session(engine) as db:
                learner = db.query(User).filter_by(user_id="offline-role-learner").one()
                learner.role = "BARBER"
                db.commit()
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/open"
            ).status_code == 404
            assert client.post(
                "/api/learner/lessons/cosmetology-foundations/steps/1/complete"
            ).status_code == 404
            assert client.post(
                "/api/learner/lessons/barber-foundations/open"
            ).status_code == 200
            assert client.get("/api/owner/curriculum/progress-summary").status_code == 403
    finally:
        engine.dispose()
