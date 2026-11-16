"""Payload-binding storage checks on guarded disposable PostgreSQL.

Identity/CSRF/session assertions remain synthetic fixture inputs; this does not
verify fresh MFA or expose a payment route or a real provider.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pytest
import sqlalchemy as sa

from tests.payment_action_binding_fixture import (
    create_action_binding_test_schema, issue_for_verified_fixture,
    consume_for_verified_fixture,
)
from tests.test_payment_action_payload_binding import ACTION, KEY, OWNER, FakeProvider
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


@pytest.fixture
def action_binding_postgres(isolated_logout_engine):
    engine = isolated_logout_engine
    create_action_binding_test_schema(engine)
    token = issue_for_verified_fixture(
        engine, user_id=OWNER["user_id"], session_id="synthetic-session",
        action=dict(ACTION), key=KEY, now=100,
    )
    return engine, token, FakeProvider()


def consume(fixture, *, action=None, now=101):
    engine, token, provider = fixture
    return consume_for_verified_fixture(
        engine, user=OWNER, session_id="synthetic-session", token=token,
        action=dict(ACTION) if action is None else action, key=KEY, now=now,
        csrf_verified=True, session_active=True,
    )


@pytest.mark.parametrize("change", [
    {"destination_ref": "synthetic-destination-b"},
    {"provider_ref": "fake-provider-b"},
    {"currency": "EUR"},
])
def test_postgres_changed_action_preserves_approved_proof(action_binding_postgres, change):
    engine, token, provider = action_binding_postgres
    assert not consume(action_binding_postgres, action={**ACTION, **change})
    assert provider.changes == []
    with engine.connect() as db:
        assert db.scalar(sa.text(
            "SELECT used_at FROM payment_action_bound_proofs_test"
        )) is None
    assert consume(action_binding_postgres)
    provider.configure(ACTION)
    assert not consume(action_binding_postgres)
    assert provider.changes == [ACTION]


def test_postgres_eight_consumers_allow_one_fake_provider_change(action_binding_postgres):
    engine, token, provider = action_binding_postgres
    start = Barrier(8)
    dispatch_lock = Lock()

    def attempt():
        start.wait(timeout=10)
        allowed = consume(action_binding_postgres)
        if allowed:
            with dispatch_lock:
                provider.configure(ACTION)
        return allowed

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(attempt) for _ in range(8)]
        outcomes = [future.result(timeout=20) for future in futures]
    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 7
    assert provider.changes == [ACTION]
    with engine.connect() as db:
        assert db.scalar(sa.text(
            "SELECT used_at FROM payment_action_bound_proofs_test"
        )) == 101
    assert not consume(action_binding_postgres)
    assert provider.changes == [ACTION]


def test_postgres_rejected_write_rolls_back_before_fake_provider(action_binding_postgres):
    engine, token, provider = action_binding_postgres
    with engine.begin() as db:
        db.execute(sa.text(
            "ALTER TABLE payment_action_bound_proofs_test "
            "ADD CONSTRAINT reject_action_consumption CHECK (used_at IS NULL)"
        ))
    try:
        with pytest.raises(sa.exc.IntegrityError) as error:
            allowed = consume(action_binding_postgres)
            if allowed:
                provider.configure(ACTION)
        assert error.value.orig.sqlstate == "23514"
        assert provider.changes == []
        with engine.connect() as db:
            assert db.scalar(sa.text(
                "SELECT used_at FROM payment_action_bound_proofs_test"
            )) is None
    finally:
        with engine.begin() as db:
            db.execute(sa.text(
                "ALTER TABLE payment_action_bound_proofs_test DROP CONSTRAINT reject_action_consumption"
            ))
    assert consume(action_binding_postgres)
    provider.configure(ACTION)
    assert not consume(action_binding_postgres)
    assert provider.changes == [ACTION]


def test_postgres_action_proof_denied_at_exact_expiry(action_binding_postgres):
    engine, token, provider = action_binding_postgres
    assert not consume(action_binding_postgres, now=220)
    assert provider.changes == []
    with engine.connect() as db:
        assert db.scalar(sa.text(
            "SELECT used_at FROM payment_action_bound_proofs_test"
        )) is None
