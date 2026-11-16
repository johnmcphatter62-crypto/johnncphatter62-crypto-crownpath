"""Disposable SQLite acceptance tests for atomic payment MFA challenge claims."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
import sqlalchemy as sa

from crownpath.payment_mfa_atomic_challenge_test_adapter import (
    claim_verified_challenge_test,
    create_challenge_test_schema,
)

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
BASE = dict(challenge_id="synthetic-challenge", user_id="owner-a",
            session_id="session-a", action="payments.configure",
            destination="synthetic-destination")


def seed(engine, **changes):
    record = dict(BASE, verified=1, failed_attempts=0, revoked=0,
                  expires_at=int((NOW + timedelta(minutes=2)).timestamp()))
    record.update(changes)
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO payment_mfa_challenges_test
              (challenge_id,user_id,session_id,action,destination,
               verified,failed_attempts,revoked,expires_at)
            VALUES (:challenge_id,:user_id,:session_id,:action,:destination,
                    :verified,:failed_attempts,:revoked,:expires_at)
        """), record)


@pytest.fixture
def engine(tmp_path):
    db = sa.create_engine(f"sqlite:///{tmp_path / 'challenge.db'}",
                          connect_args={"timeout": 20})
    create_challenge_test_schema(db)
    yield db
    db.dispose()


def claim(engine, **changes):
    args = dict(BASE, now=NOW)
    args.update(changes)
    return claim_verified_challenge_test(engine, **args)


def test_first_claim_succeeds_and_replay_fails(engine):
    seed(engine)
    assert claim(engine)
    assert not claim(engine)


@pytest.mark.parametrize("change", [
    {"verified": 0}, {"revoked": 1}, {"failed_attempts": 5},
    {"failed_attempts": -1},
    {"expires_at": int(NOW.timestamp())},
])
def test_unverified_revoked_rate_limited_or_expired_denied(engine, change):
    seed(engine, **change)
    assert not claim(engine)


@pytest.mark.parametrize("change", [
    {"user_id": "owner-b"}, {"session_id": "session-b"},
    {"action": "payments.refund"}, {"destination": "other-destination"},
])
def test_mismatch_denied_without_consuming(engine, change):
    seed(engine)
    assert not claim(engine, **change)
    assert claim(engine)


def test_two_competing_claims_allow_exactly_one(engine):
    seed(engine)
    barrier = Barrier(2)

    def compete():
        barrier.wait(timeout=15)
        return claim(engine)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(compete)
        second = pool.submit(compete)
        results = [first.result(timeout=25), second.result(timeout=25)]
    assert sorted(results) == [False, True]
    assert not claim(engine)
