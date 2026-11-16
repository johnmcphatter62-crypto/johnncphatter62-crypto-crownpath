"""Actual logout HTTP contract under injected database failures.

Uses authentically issued synthetic sessions and disposable SQLite records.
This does not integrate the experimental payment-proof adapter into routes.
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
from crownpath.models import AuditEvent, User


@pytest.mark.parametrize("failure_point", ["decode_access_token", "revoke_access_token"])
@pytest.mark.parametrize("failure_kind", ["lock_timeout", "connection_loss"])
def test_logout_database_failure_preserves_session_cookie_and_retry(
    monkeypatch, tmp_path, failure_point, failure_kind,
):
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'synthetic_http_logout_failure.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-http-logout-failure-key")
    marker = "synthetic-private-database-error"
    original = (
        psycopg.errors.LockNotAvailable(marker)
        if failure_kind == "lock_timeout"
        else psycopg.OperationalError(marker)
    )
    failure = sa.exc.OperationalError("synthetic-only statement", {}, original)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="http-failure-owner", name="Synthetic Owner",
                email="http-failure@example.invalid", password_hash="synthetic-only",
                role="OWNER", active=True, mfa_enabled=True,
            ))
            db.commit()
        token = auth.create_access_token("http-failure-owner")
        untouched = auth.create_access_token("http-failure-owner")
        assert auth.decode_access_token(token) == "http-failure-owner"
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            client.cookies.set("crownpath_session", token)
            with patch.object(main, failure_point, side_effect=failure) as failing:
                with patch.object(main, "record_audit") as record:
                    response = client.post("/api/auth/logout")
                    failing.assert_called_once()
                    record.assert_not_called()
            assert response.status_code == 503
            assert response.json() == {"detail": "Logout could not be confirmed. Please retry."}
            assert marker not in response.text
            assert token not in response.text
            assert "authenticated" not in response.json()
            assert not any(
                "crownpath_session=" in value
                for value in response.headers.get_list("set-cookie")
            )
            assert client.cookies.get("crownpath_session") == token
            assert auth.decode_access_token(token) == "http-failure-owner"
            assert auth.decode_access_token(untouched) == "http-failure-owner"
            with Session(engine) as db:
                assert db.scalars(sa.select(AuditEvent).where(
                    AuditEvent.action == "SESSION_LOGOUT",
                )).all() == []

            retry = client.post("/api/auth/logout")
            assert retry.status_code == 200
            assert retry.json() == {"authenticated": False}
            assert any(
                "crownpath_session=" in value and "Max-Age=0" in value
                for value in retry.headers.get_list("set-cookie")
            )
            assert auth.decode_access_token(token) is None
            assert auth.decode_access_token(untouched) == "http-failure-owner"
        with Session(engine) as db:
            events = db.scalars(sa.select(AuditEvent).where(
                AuditEvent.action == "SESSION_LOGOUT",
            )).all()
            assert len(events) == 1
            assert events[0].result == "SUCCESS"
            assert events[0].user_id == "http-failure-owner"
            assert token not in str(events[0].reason)
    finally:
        engine.dispose()
