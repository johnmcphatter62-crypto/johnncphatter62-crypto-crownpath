"""Experimental session-aware payment-proof consumption.

Test-only: caller MUST authenticate signed session and independently enforce
owner permission, fresh server-side MFA, and CSRF. No production route wiring.
"""
import hashlib
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def consume_with_active_session_test(engine, *, token, user_id, session_id, now=None):
    """Consume proof only while matching AuthToken is active, in one SQL update.

    The EXISTS predicate is evaluated in the same statement as proof mutation.
    PostgreSQL concurrency semantics still require separate integration tests.
    """
    if not all(isinstance(x, str) and x.strip() for x in (token, user_id, session_id)):
        return False
    when = datetime.now(timezone.utc) if now is None else now
    proof_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    with Session(engine) as db:
        with db.begin():
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
