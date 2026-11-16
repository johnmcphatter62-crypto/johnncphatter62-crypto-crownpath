"""Verify authentication audit events with disposable synthetic HTTP accounts."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import AuditEvent, User


def test_login_audit_success_failure_and_lockout_without_credentials(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'synthetic_auth_audit.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-auth-audit-test-only-key")
    secret = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-owner-audit",
                name="Synthetic Audit Owner",
                email="audit-owner@example.com",
                password_hash=auth.hash_password(secret),
                role="OWNER",
                active=True,
                mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            ok = client.post("/api/auth/login", json={
                "email": "audit-owner@example.com", "password": secret,
            })
            assert ok.status_code == 200, ok.text
            for _ in range(auth.MAX_FAILED_ATTEMPTS):
                bad = client.post("/api/auth/login", json={
                    "email": "audit-owner@example.com",
                    "password": "WrongSyntheticPassword!",
                })
                assert bad.status_code == 401, bad.text
            locked = client.post("/api/auth/login", json={
                "email": "audit-owner@example.com", "password": secret,
            })
            assert locked.status_code == 423, locked.text
        with Session(engine) as db:
            rows = db.scalars(select(AuditEvent).order_by(AuditEvent.audit_id)).all()
            actions = [row.action for row in rows]
            assert "LOGIN_SUCCESS" in actions
            assert actions.count("LOGIN_FAILED") == auth.MAX_FAILED_ATTEMPTS
            assert "LOGIN_LOCKED" in actions
            serialized = " ".join(str(getattr(row, col)) for row in rows for col in (
                "action", "category", "result", "reason", "resource_id"
            ))
            assert secret not in serialized
            assert "WrongSyntheticPassword!" not in serialized
    finally:
        engine.dispose()
