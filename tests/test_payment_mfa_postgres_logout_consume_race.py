"""Deterministic transaction-order checks on disposable PostgreSQL only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event, local
from time import monotonic

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


@pytest.mark.parametrize("leader", ["logout", "consume"])
def test_postgres_logout_consume_commit_order(isolated_logout_engine, monkeypatch, leader):
    import jwt
    from crownpath import auth
    from crownpath.models import AuthToken, User
    from crownpath.payment_mfa_db_proof import issue_verified_proof
    from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test
    from crownpath.payment_mfa_session_aware_consume_test import consume_with_active_session_test

    engine = isolated_logout_engine
    monkeypatch.setattr(auth, "session", sessionmaker(bind=engine))
    with Session(engine) as db:
        db.add(User(user_id="race-owner", name="Synthetic Race Owner",
                    email="race-owner@example.invalid", password_hash="synthetic-only",
                    role="OWNER", active=True, mfa_enabled=True))
        db.commit()
    token = auth.create_access_token("race-owner")
    untouched = auth.create_access_token("race-owner")
    assert auth.decode_access_token(token) == "race-owner"
    jti = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])["jti"]
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    proof = issue_verified_proof(engine, user_id="race-owner", session_id=jti, now=timestamp)
    locked, follower_started, release = Event(), Event(), Event()
    role = local()
    pids = {}
    follower = "consume" if leader == "logout" else "logout"

    def session_lock_statement(statement):
        normalized = " ".join(statement.upper().split())
        return normalized.startswith("UPDATE AUTH_TOKENS ") or (
            normalized.startswith("SELECT AUTH_TOKENS.TOKEN_ID")
            and "FOR UPDATE" in normalized
        )

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        operation = getattr(role, "operation", None)
        if operation and session_lock_statement(statement):
            pids[operation] = conn.connection.driver_connection.info.backend_pid
            if operation == follower:
                follower_started.set()

    def after_cursor(conn, cursor, statement, parameters, context, executemany):
        if getattr(role, "operation", None) == leader and session_lock_statement(statement):
            locked.set()
            assert release.wait(timeout=10), "Controller did not release session lock"

    def operate(operation):
        role.operation = operation
        if operation == "logout":
            return revoke_session_and_proofs_test(
                engine, user_id="race-owner", session_id=jti, now=now,
            )
        return consume_with_active_session_test(
            engine, token=proof, user_id="race-owner", session_id=jti, now=now,
        )

    sa.event.listen(engine, "before_cursor_execute", before_cursor)
    sa.event.listen(engine, "after_cursor_execute", after_cursor)
    pool = ThreadPoolExecutor(max_workers=2)
    try:
        first = pool.submit(operate, leader)
        assert locked.wait(timeout=5), "Leader did not acquire session row lock"
        second = pool.submit(operate, follower)
        assert follower_started.wait(timeout=5), "Follower did not attempt session lock"
        # Observe real database blocking, rather than assume thread scheduling.
        deadline = monotonic() + 3
        blocked = False
        with engine.connect() as monitor:
            while monotonic() < deadline:
                blockers = monitor.scalar(sa.text(
                    "SELECT pg_blocking_pids(:pid)"
                ), {"pid": pids[follower]})
                if pids[leader] in blockers:
                    blocked = True
                    break
                release.wait(timeout=0.01)
        assert blocked, "Competing transaction did not wait on the session row"
        release.set()
        results = {leader: first.result(timeout=15), follower: second.result(timeout=15)}
        assert results["logout"] is True
        assert results["consume"] is (leader == "consume")
    finally:
        release.set()
        pool.shutdown(wait=True, cancel_futures=True)
        sa.event.remove(engine, "before_cursor_execute", before_cursor)
        sa.event.remove(engine, "after_cursor_execute", after_cursor)

    assert auth.decode_access_token(token) is None
    assert auth.decode_access_token(untouched) == "race-owner"
    assert not consume_with_active_session_test(
        engine, token=proof, user_id="race-owner", session_id=jti, now=now,
    )
    with engine.connect() as conn:
        assert conn.scalar(sa.text(
            "SELECT used_at FROM payment_mfa_proofs_test WHERE session_id=:sid"
        ), {"sid": jti}) == timestamp
        assert conn.scalar(sa.select(AuthToken.used_at).where(
            AuthToken.token_hash == auth._hash_session_id(jti),
        )) == now
