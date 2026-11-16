"""Logout audit-write failure must roll back revocation and permit retry.

Uses injected audit INSERT failures and disposable SQLite records only.
"""
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
def test_logout_audit_failure_rolls_back_and_retries(
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

    def fail_audit_insert(conn, cursor, statement, parameters, context, executemany):
        if not statement.lstrip().upper().startswith("INSERT INTO AUDIT_EVENTS"):
            return
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
            sa.event.listen(engine, "before_cursor_execute", fail_audit_insert)
            try:
                failed = client.post("/api/auth/logout")
            finally:
                sa.event.remove(engine, "before_cursor_execute", fail_audit_insert)
            assert attempts == ["audit-write"]
            assert failed.status_code == 503
            assert failed.json() == {"detail": "Logout could not be confirmed. Please retry."}
            assert marker not in failed.text and token not in failed.text
            assert not any(
                "crownpath_session=" in value
                for value in failed.headers.get_list("set-cookie")
            )
            assert client.cookies.get("crownpath_session") == token
            # Audit INSERT failure must roll back the earlier session UPDATE.
            assert auth.decode_access_token(token) == "audit-failure-owner"
            assert auth.decode_access_token(untouched) == "audit-failure-owner"
            with Session(engine) as db:
                revoked = db.scalars(sa.select(AuthToken).where(
                    AuthToken.user_id == "audit-failure-owner",
                    AuthToken.used_at.is_not(None),
                )).all()
                assert revoked == []
            assert logout_events() == []

            # After audit recovery, retry commits both effects exactly once.
            retry = client.post("/api/auth/logout")
            assert retry.status_code == 200
            assert retry.json() == {"authenticated": False}
            assert any(
                "crownpath_session=" in value and "Max-Age=0" in value
                for value in retry.headers.get_list("set-cookie")
            )
            assert auth.decode_access_token(token) is None
            assert auth.decode_access_token(untouched) == "audit-failure-owner"
            events = logout_events()
            assert len(events) == 1
            assert events[0].result == "SUCCESS"
            assert events[0].user_id == "audit-failure-owner"
            assert token not in str(events[0].reason)
            client.cookies.set("crownpath_session", token)
            replay = client.post("/api/auth/logout")
            assert replay.status_code == 200
            assert auth.decode_access_token(token) is None
            assert len(logout_events()) == 1
    finally:
        engine.dispose()
