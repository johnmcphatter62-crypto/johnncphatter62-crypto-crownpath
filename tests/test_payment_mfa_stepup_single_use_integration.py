"""Disposable integration of fresh step-up policy and atomic proof consumption.

No real MFA verification, app database, HTTP route, or payment provider.
"""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, consume_proof, issue_verified_proof,
)
from crownpath.payment_mfa_stepup_test_policy import fresh_payment_stepup


def test_fresh_stepup_allows_one_proof_use_only(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'single_use.db'}")
    try:
        create_test_schema(engine)
        now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
        verified = {
            "verified": True, "consumed": False,
            "user_id": "owner-a", "session_id": "session-a",
            "action": "payments.configure",
            "verified_at": now - timedelta(seconds=30),
        }
        assert fresh_payment_stepup(
            verified, user_id="owner-a", session_id="session-a",
            action="payments.configure", now=now,
        )
        timestamp = int(now.timestamp())
        token = issue_verified_proof(
            engine, user_id="owner-a", session_id="session-a", now=timestamp,
        )
        assert not consume_proof(engine, token=token, user_id="owner-b",
                                 session_id="session-a", now=timestamp)
        assert not consume_proof(engine, token=token, user_id="owner-a",
                                 session_id="session-b", now=timestamp)
        assert consume_proof(engine, token=token, user_id="owner-a",
                             session_id="session-a", now=timestamp)
        assert not consume_proof(engine, token=token, user_id="owner-a",
                                 session_id="session-a", now=timestamp)
        assert not consume_proof(engine, token=token, user_id="owner-a",
                                 session_id="session-a", now=timestamp + 121)
    finally:
        engine.dispose()


def test_stale_stepup_denied_before_proof_issue(tmp_path):
    # No proof is issued for a stale synthetic step-up record.
    now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    record = {
        "verified": True, "consumed": False, "user_id": "owner-a",
        "session_id": "session-a", "action": "payments.configure",
        "verified_at": now - timedelta(seconds=121),
    }
    assert not fresh_payment_stepup(record, user_id="owner-a",
                                   session_id="session-a",
                                   action="payments.configure", now=now)
