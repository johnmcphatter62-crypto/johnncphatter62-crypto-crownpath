"""Disabled synthetic accounts cannot reuse sessions to access protected pages."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_disabled_account_cannot_reuse_old_session(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'disabled_session_http.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "isolated-disabled-session-key")
    monkeypatch.setattr(main, "role_access_approved", lambda role: True)
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-disabled-learner",
                name="Synthetic Disabled Learner",
                email="disabled-learner@example.com",
                password_hash=auth.hash_password(password),
                role="COSMETOLOGY_PRO", active=True, mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "disabled-learner@example.com", "password": password,
            })
            assert login.status_code == 200, login.text
            token = client.cookies.get("crownpath_session")
            assert token and auth.decode_access_token(token) == "synthetic-disabled-learner"
            before = client.get("/api/learner/dashboard")
            assert before.status_code == 200, before.text

            auth.set_user_active("synthetic-disabled-learner", False)
            assert auth.decode_access_token(token) is None
            after = client.get("/api/learner/dashboard")
            assert after.status_code in (401, 403), after.text
            denied = client.post("/api/auth/login", json={
                "email": "disabled-learner@example.com", "password": password,
            })
            assert denied.status_code in (401, 403, 423), denied.text
    finally:
        engine.dispose()
