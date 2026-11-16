"""Verify logout audit persistence and token revocation in disposable SQLite."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import AuditEvent, User


def test_logout_records_event_and_revokes_cookie_session(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'synthetic_logout_audit.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "isolated-logout-audit-key")
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-logout-owner", name="Synthetic Logout Owner",
                email="logout-audit@example.com",
                password_hash=auth.hash_password(password),
                role="OWNER", active=True, mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "logout-audit@example.com", "password": password,
            })
            assert login.status_code == 200, login.text
            token = client.cookies.get("crownpath_session")
            assert token and auth.decode_access_token(token) == "synthetic-logout-owner"
            logout = client.post("/api/auth/logout")
            assert logout.status_code == 200, logout.text
            assert auth.decode_access_token(token) is None
        with Session(engine) as db:
            events = db.scalars(
                select(AuditEvent).where(AuditEvent.action == "SESSION_LOGOUT")
            ).all()
            assert len(events) == 1
            assert events[0].user_id == "synthetic-logout-owner"
            assert events[0].result == "SUCCESS"
            assert token not in str(events[0].reason)
            assert password not in str(events[0].reason)
    finally:
        engine.dispose()
