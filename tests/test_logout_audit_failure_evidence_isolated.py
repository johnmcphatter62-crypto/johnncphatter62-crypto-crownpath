"""Diagnostic evidence for an OPEN logout/audit release blocker.

These assertions characterize the current failure, not desired acceptance.
Replace them with atomic-failure acceptance tests when remediation is added.
No live routes, credentials or production databases are changed.
"""
from unittest.mock import patch

import psycopg
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import AuditEvent, AuthToken, User


@pytest.mark.parametrize("failure_kind", ["lock_timeout", "connection_loss"])
def test_current_logout_audit_failure_leaves_missing_event(
    monkeypatch, tmp_path, failure_kind,
):
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'synthetic_audit_failure.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-logout-audit-failure-key")
    marker = "synthetic-private-audit-error"
    attempts = []

    class FailingAuditSession(Session):
        def commit(self):
            attempts.append("audit-write")
            original = (
                psycopg.errors.LockNotAvailable(marker)
                if failure_kind == "lock_timeout"
                else psycopg.OperationalError(marker)
            )
            raise sa.exc.OperationalError("synthetic audit insert", {}, original)

    def logout_events():
        with Session(engine) as db:
            return db.scalars(sa.select(AuditEvent).where(
                AuditEvent.action == "SESSION_LOGOUT",
            )).all()

    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="audit-failure-owner", name="Synthetic Owner",
                email="audit-failure@example.invalid", password_hash="synthetic-only",
                role="OWNER", active=True, mfa_enabled=True,
            ))
            db.commit()
        token = auth.create_access_token("audit-failure-owner")
        untouched = auth.create_access_token("audit-failure-owner")
        assert auth.decode_access_token(token) == "audit-failure-owner"
        with TestClient(
            main.app, headers={"Origin": "http://testserver"},
            raise_server_exceptions=False,
        ) as client:
            client.cookies.set("crownpath_session", token)
            with patch.object(audit, "session", lambda: FailingAuditSession(engine)):
                failed = client.post("/api/auth/logout")
            assert attempts == ["audit-write"]
            assert failed.status_code == 500
            assert marker not in failed.text and token not in failed.text
            assert not any(
                "crownpath_session=" in value
                for value in failed.headers.get_list("set-cookie")
            )
            assert client.cookies.get("crownpath_session") == token
            # Current gap: revocation committed before the audit transaction.
            assert auth.decode_access_token(token) is None
            assert auth.decode_access_token(untouched) == "audit-failure-owner"
            with Session(engine) as db:
                revoked = db.scalar(sa.select(AuthToken).where(
                    AuthToken.user_id == "audit-failure-owner",
                    AuthToken.used_at.is_not(None),
                ))
                assert revoked is not None
            assert logout_events() == []

            # Even after the audit store recovers, replay skips audit creation
            # because the session has already been revoked.
            retry = client.post("/api/auth/logout")
            assert retry.status_code == 200
            assert retry.json() == {"authenticated": False}
            assert any(
                "crownpath_session=" in value and "Max-Age=0" in value
                for value in retry.headers.get_list("set-cookie")
            )
            assert auth.decode_access_token(token) is None
            assert auth.decode_access_token(untouched) == "audit-failure-owner"
            assert logout_events() == []
    finally:
        engine.dispose()
