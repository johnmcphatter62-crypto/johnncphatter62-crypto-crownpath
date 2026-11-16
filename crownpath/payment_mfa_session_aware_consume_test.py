"""Experimental session-aware payment-proof consumption.

Test-only: caller MUST authenticate signed session and independently enforce
owner permission, fresh server-side MFA, and CSRF. No production route wiring.
"""
import hashlib
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from crownpath.auth import _hash_session_id


def consume_with_active_session_test(engine, *, token, user_id, session_id, now=None):
    """Consume only with an active session in the same transaction.

    PostgreSQL locks the session before the proof to serialize with logout.
    SQLite retains its existing conditional-update test behavior.
    """
    if not all(isinstance(x, str) and x.strip() for x in (token, user_id, session_id)):
        return False
    when = datetime.now(timezone.utc) if now is None else now
    proof_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session_hash = _hash_session_id(session_id)
    with Session(engine) as db:
        with db.begin():

            # Match logout's lock order: session row first, then proof row.
            # A concurrent logout must finish before this session can be used.
            if engine.dialect.name == "postgresql":
                from sqlalchemy import select
                from crownpath.models import AuthToken
                active = db.scalar(
                    select(AuthToken.token_id).where(
                        AuthToken.user_id == user_id,
                        AuthToken.token_hash == session_hash,
                        AuthToken.token_type == "SESSION",
                        AuthToken.used_at.is_(None),
                        AuthToken.expires_at > when,
                    ).with_for_update()
                )
                if active is None:
                    return False
            result = db.execute(text("""
                UPDATE payment_mfa_proofs_test
                   SET used_at = :timestamp
                 WHERE proof_hash = :proof_hash
                   AND user_id = :user_id
                   AND session_id = :session_id
                   AND purpose = 'payments.configure'
                   AND used_at IS NULL
                   AND expires_at > :timestamp
                   AND EXISTS (
                       SELECT 1 FROM auth_tokens
                        WHERE user_id = :user_id
                          AND token_hash = :session_hash
                          AND token_type = 'SESSION'
                          AND used_at IS NULL
                          AND expires_at > :when
                   )
            """), {
                "timestamp": int(when.timestamp()), "when": when,
                "proof_hash": proof_hash, "session_hash": session_hash,
                "user_id": user_id, "session_id": session_id,
            })
            return result.rowcount == 1
