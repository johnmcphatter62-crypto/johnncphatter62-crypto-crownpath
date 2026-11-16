"""Actual HTTP logout transactions in a guarded disposable PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


@pytest.fixture
def postgres_http_logout(isolated_logout_engine, monkeypatch):
    import crownpath.audit as audit
    import crownpath.auth as auth
    import crownpath.main as main
    from crownpath.models import AuditEvent, User

    engine = isolated_logout_engine
    AuditEvent.__table__.create(engine)
    with engine.connect() as conn:
        schema = conn.scalar(sa.text("SELECT current_schema()"))
    worker = sa.create_engine(engine.url, connect_args={
        "connect_timeout": 5,
        "options": f"-csearch_path={schema} -clock_timeout=150 -cstatement_timeout=2000",
    })
    monkeypatch.setattr(auth, "session", sessionmaker(bind=worker))
    monkeypatch.setattr(audit, "session", sessionmaker(bind=worker))
    monkeypatch.setattr(main, "session", sessionmaker(bind=worker))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-postgres-http-logout-key")
    try:
        with Session(engine) as db:
            db.add(User(
                user_id="pg-http-owner", name="Synthetic PostgreSQL Owner",
                email="pg-http@example.invalid", password_hash="synthetic-only",
                role="OWNER", active=True, mfa_enabled=True,
            ))
            db.commit()
        token = auth.create_access_token("pg-http-owner")
        untouched = auth.create_access_token("pg-http-owner")
        assert auth.decode_access_token(token) == "pg-http-owner"
        yield engine, worker, auth, main, token, untouched
    finally:
        worker.dispose()


@pytest.mark.parametrize("failure_kind", ["constraint", "lock_timeout"])
def test_postgres_http_audit_failure_rolls_back_and_retries(postgres_http_logout, failure_kind):
    from fastapi.testclient import TestClient
    from crownpath.models import AuditEvent, AuthToken

    engine, worker, auth, main, token, untouched = postgres_http_logout
    errors = []

    def capture_error(context):
        errors.append(getattr(context.original_exception, "sqlstate", None))

    def events():
        with Session(engine) as db:
            return db.scalars(sa.select(AuditEvent).where(
                AuditEvent.action == "SESSION_LOGOUT",
            )).all()

    blocker = None
    transaction = None
    constraint = False
    sa.event.listen(worker, "handle_error", capture_error)
    try:
        if failure_kind == "constraint":
            with engine.begin() as conn:
                conn.execute(sa.text(
                    "ALTER TABLE audit_events ADD CONSTRAINT reject_logout_audit "
                    "CHECK (action <> 'SESSION_LOGOUT')"
                ))
            constraint = True
        else:
            blocker = engine.connect()
            transaction = blocker.begin()
            blocker.execute(sa.text("LOCK TABLE audit_events IN ACCESS EXCLUSIVE MODE"))

        with TestClient(
            main.app, headers={"Origin": "http://testserver"},
            raise_server_exceptions=False,
        ) as client:
            client.cookies.set("crownpath_session", token)
            try:
                failed = client.post("/api/auth/logout")
            finally:
                if transaction is not None:
                    transaction.rollback()
                    transaction = None
                if blocker is not None:
                    blocker.close()
                    blocker = None
                if constraint:
                    with engine.begin() as conn:
                        conn.execute(sa.text(
                            "ALTER TABLE audit_events DROP CONSTRAINT reject_logout_audit"
                        ))
                    constraint = False

            assert errors == ["23514" if failure_kind == "constraint" else "55P03"]
            assert failed.status_code == 503
            assert failed.json() == {"detail": "Logout could not be confirmed. Please retry."}
            assert token not in failed.text and untouched not in failed.text
            assert not any(
                "crownpath_session=" in value
                for value in failed.headers.get_list("set-cookie")
            )
            assert client.cookies.get("crownpath_session") == token
            assert auth.decode_access_token(token) == "pg-http-owner"
            assert auth.decode_access_token(untouched) == "pg-http-owner"
            with Session(engine) as db:
                assert db.scalars(sa.select(AuthToken).where(
                    AuthToken.user_id == "pg-http-owner", AuthToken.used_at.is_not(None),
                )).all() == []
            assert events() == []

            retry = client.post("/api/auth/logout")
            assert retry.status_code == 200
            assert retry.json() == {"authenticated": False}
            assert any(
                "crownpath_session=" in value and "Max-Age=0" in value
                for value in retry.headers.get_list("set-cookie")
            )
            assert auth.decode_access_token(token) is None
            assert auth.decode_access_token(untouched) == "pg-http-owner"
            saved = events()
            assert len(saved) == 1
            assert saved[0].user_id == "pg-http-owner" and saved[0].result == "SUCCESS"
            assert token not in str(saved[0].reason)

            client.cookies.set("crownpath_session", token)
            replay = client.post("/api/auth/logout")
            assert replay.status_code == 200
            assert len(events()) == 1
    finally:
        if transaction is not None:
            transaction.rollback()
        if blocker is not None:
            blocker.close()
        if constraint:
            with engine.begin() as conn:
                conn.execute(sa.text("ALTER TABLE audit_events DROP CONSTRAINT reject_logout_audit"))
        sa.event.remove(worker, "handle_error", capture_error)


def test_postgres_two_http_logouts_write_exactly_one_event(postgres_http_logout):
    from fastapi.testclient import TestClient
    from crownpath.models import AuditEvent

    engine, worker, auth, main, token, untouched = postgres_http_logout
    start = Barrier(2)

    def logout():
        with TestClient(
            main.app, headers={"Origin": "http://testserver"},
            raise_server_exceptions=False,
        ) as client:
            client.cookies.set("crownpath_session", token)
            start.wait(timeout=10)
            response = client.post("/api/auth/logout")
            assert response.json() == {"authenticated": False}
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(logout)
        second = pool.submit(logout)
        assert [first.result(timeout=15), second.result(timeout=15)] == [200, 200]
    assert auth.decode_access_token(token) is None
    assert auth.decode_access_token(untouched) == "pg-http-owner"
    with Session(engine) as db:
        events = db.scalars(sa.select(AuditEvent).where(
            AuditEvent.action == "SESSION_LOGOUT",
        )).all()
        assert len(events) == 1
        assert events[0].user_id == "pg-http-owner"
        assert events[0].result == "SUCCESS"
