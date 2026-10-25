"""Experimental database-backed, session-bound payment MFA proofs.

Not connected to routes or real payments. Caller must independently verify MFA
and authenticate the owner before issuing a proof. Requires an isolated table
created by the caller; does not migrate or access production data.
"""
import hashlib
import secrets
import time

from sqlalchemy import text

PURPOSE = "payments.configure"

def create_test_schema(engine):
    """Only call on disposable test databases; NOT a production migration."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE payment_mfa_proofs_test (
                proof_hash VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                session_id VARCHAR(128) NOT NULL,
                purpose VARCHAR(64) NOT NULL,
                expires_at BIGINT NOT NULL,
                used_at BIGINT
            )
        """))

def issue_verified_proof(engine, *, user_id, session_id, now=None, ttl_seconds=120):
    """Issue only AFTER a separate trusted server-side MFA check succeeds."""
    if not user_id or not session_id or ttl_seconds <= 0:
        raise ValueError("Valid owner/session scope and TTL required")
    timestamp = int(time.time()) if now is None else int(now)
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO payment_mfa_proofs_test
                (proof_hash, user_id, session_id, purpose, expires_at, used_at)
            VALUES (:digest, :user_id, :session_id, :purpose, :expiry, NULL)
        """), dict(digest=digest, user_id=user_id, session_id=session_id,
                   purpose=PURPOSE, expiry=timestamp + ttl_seconds))
    return token

def consume_proof(engine, *, token, user_id, session_id, now=None, purpose=PURPOSE):
    """Atomically consume a matching proof; all mismatches deny and do not consume."""
    if not token or not user_id or not session_id or purpose != PURPOSE:
        return False
    timestamp = int(time.time()) if now is None else int(now)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE payment_mfa_proofs_test SET used_at = :now
            WHERE proof_hash = :digest AND user_id = :user_id
              AND session_id = :session_id AND purpose = :purpose
              AND used_at IS NULL AND expires_at > :now
        """), dict(now=timestamp, digest=digest, user_id=user_id,
                   session_id=session_id, purpose=purpose))
        return result.rowcount == 1

def revoke_session_proofs(engine, *, user_id, session_id, now=None):
    """Invalidate all unused payment proofs for a specific authenticated session.

    Caller must first authenticate the session server-side; never trust a
    client-supplied user or session identifier. Test schema only.
    """
    if not user_id or not session_id:
        return 0
    timestamp = int(time.time()) if now is None else int(now)
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE payment_mfa_proofs_test SET used_at = :now
            WHERE user_id = :user_id AND session_id = :session_id
              AND used_at IS NULL
        """), dict(now=timestamp, user_id=user_id, session_id=session_id))
        return result.rowcount
