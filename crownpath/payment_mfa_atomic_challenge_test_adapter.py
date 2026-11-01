"""Disposable SQLite payment MFA challenge claim adapter.

No real MFA verification, production route, provider call, or migration.
Caller must authenticate the Owner, session, CSRF and verify MFA server-side.
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session


def create_challenge_test_schema(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS payment_mfa_challenges_test (
                challenge_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                action TEXT NOT NULL,
                destination TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                expires_at INTEGER NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                consumed_at INTEGER
            )
        """))


def claim_verified_challenge_test(engine, *, challenge_id, user_id,
                                  session_id, action, destination, now=None,
                                  max_failures=5):
    values = (challenge_id, user_id, session_id, action, destination)
    if not all(isinstance(v, str) and v.strip() for v in values):
        return False
    if type(max_failures) is not int or not 1 <= max_failures <= 10:
        return False
    when = datetime.now(timezone.utc) if now is None else now
    if not isinstance(when, datetime) or when.tzinfo is None:
        return False
    with Session(engine) as db:
        with db.begin():
            result = db.execute(sa.text("""
                UPDATE payment_mfa_challenges_test
                SET consumed_at = :now
                WHERE challenge_id = :challenge_id
                  AND user_id = :user_id
                  AND session_id = :session_id
                  AND action = :action
                  AND destination = :destination
                  AND verified = 1
                  AND revoked = 0
                  AND consumed_at IS NULL
                  AND failed_attempts >= 0
                  AND failed_attempts < :max_failures
                  AND expires_at > :now
            """), dict(now=int(when.timestamp()), challenge_id=challenge_id,
                       user_id=user_id, session_id=session_id, action=action,
                       destination=destination, max_failures=max_failures))
            return result.rowcount == 1
