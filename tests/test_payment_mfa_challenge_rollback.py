"""Isolated transaction rollback tests for synthetic MFA challenge claims."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.payment_mfa_atomic_challenge_test_adapter import (
    claim_verified_challenge_test,
    create_challenge_test_schema,
)

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
PARAMS = dict(challenge_id="synthetic", user_id="owner", session_id="session",
              action="payments.configure", destination="destination", now=NOW)


def test_claim_and_audit_rollback_together(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'rollback.db'}")
    try:
        create_challenge_test_schema(engine)
        with engine.begin() as conn:
            conn.execute(sa.text("""
                INSERT INTO payment_mfa_challenges_test
                (challenge_id,user_id,session_id,action,destination,
                 verified,failed_attempts,expires_at)
                VALUES ('synthetic','owner','session','payments.configure',
                        'destination',1,0,:expiry)
            """), {"expiry": int((NOW + timedelta(minutes=2)).timestamp())})
            conn.execute(sa.text("""
                CREATE TABLE payment_audit_test (
                    event_id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL)
            """))
        with pytest.raises(RuntimeError, match="synthetic audit failure"):
            with Session(engine) as db:
                with db.begin():
                    result = db.execute(sa.text("""
                        UPDATE payment_mfa_challenges_test
                        SET consumed_at = :now
                        WHERE challenge_id = 'synthetic'
                          AND consumed_at IS NULL
                          AND verified = 1 AND expires_at > :now
                    """), {"now": int(NOW.timestamp())})
                    assert result.rowcount == 1
                    db.execute(sa.text("""
                        INSERT INTO payment_audit_test (event_id,challenge_id)
                        VALUES ('event-1','synthetic')
                    """))
                    raise RuntimeError("synthetic audit failure")
        with engine.connect() as conn:
            assert conn.scalar(sa.text("""
                SELECT consumed_at FROM payment_mfa_challenges_test
                WHERE challenge_id = 'synthetic'
            """)) is None
            assert conn.scalar(sa.text("SELECT count(*) FROM payment_audit_test")) == 0
        assert claim_verified_challenge_test(engine, **PARAMS)
        assert not claim_verified_challenge_test(engine, **PARAMS)
    finally:
        engine.dispose()
