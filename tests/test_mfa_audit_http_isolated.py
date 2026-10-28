"""HTTP MFA audit regression checks using synthetic accounts and disposable SQLite."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import pyotp

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import AuditEvent, User


def test_mfa_http_audit_records_exclude_codes(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'synthetic_mfa_audit.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "isolated-mfa-audit-key")
    secret = pyotp.random_base32()
    password = "SyntheticMfaPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-mfa-owner",
                name="Synthetic MFA Owner",
                email="mfa-audit@example.com",
                password_hash=auth.hash_password(password),
                role="OWNER",
                active=True,
                mfa_enabled=True,
                mfa_secret=secret,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "mfa-audit@example.com", "password": password,
            })
            assert login.status_code == 200, login.text
            challenge = login.json()["challenge"]
            assert login.json()["mfa_required"] is True
            failed = client.post("/api/auth/mfa/verify", json={
                "challenge": challenge, "code": "not-a-valid-code",
            })
            assert failed.status_code == 401, failed.text
            valid_code = pyotp.TOTP(secret).now()
            success = client.post("/api/auth/mfa/verify", json={
                "challenge": challenge, "code": valid_code,
            })
            assert success.status_code == 200, success.text
            assert success.json()["authenticated"] is True
        with Session(engine) as db:
            events = db.scalars(select(AuditEvent).order_by(AuditEvent.audit_id)).all()
            actions = [event.action for event in events]
            assert "MFA_CHALLENGE_ISSUED" in actions
            assert "MFA_VERIFY_FAILED" in actions
            assert "MFA_VERIFY_SUCCESS" in actions
            fields = " ".join(
                str(getattr(event, name))
                for event in events
                for name in ("action", "category", "result", "reason", "resource_id")
            )
            for credential in (password, secret, valid_code, "not-a-valid-code", challenge):
                assert credential not in fields
    finally:
        engine.dispose()
