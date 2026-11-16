"""Role changes invalidate old sessions and update protected dashboard access."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_role_change_revokes_old_session_and_updates_dashboard(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'role_change_session_http.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "isolated-role-session-key")
    monkeypatch.setattr(main, "role_access_approved", lambda role: True)
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-role-learner", name="Synthetic Role Learner",
                email="role-change-learner@example.com",
                password_hash=auth.hash_password(password),
                role="COSMETOLOGY_PRO", active=True, mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "role-change-learner@example.com", "password": password,
            })
            assert login.status_code == 200, login.text
            token = client.cookies.get("crownpath_session")
            assert token and auth.decode_access_token(token) == "synthetic-role-learner"
            before = client.get("/api/learner/dashboard")
            assert before.status_code == 200, before.text
            assert before.json()["role"] == "COSMETOLOGY_PRO"

            auth.set_user_role("synthetic-role-learner", "BARBER")
            assert auth.decode_access_token(token) is None
            old = client.get("/api/learner/dashboard")
            assert old.status_code in (401, 403), old.text

            again = client.post("/api/auth/login", json={
                "email": "role-change-learner@example.com", "password": password,
            })
            assert again.status_code == 200, again.text
            current = client.get("/api/learner/dashboard")
            assert current.status_code == 200, current.text
            assert current.json()["role"] == "BARBER"
    finally:
        engine.dispose()
