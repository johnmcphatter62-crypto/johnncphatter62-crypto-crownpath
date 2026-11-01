"""Test-only active-session proof consumption with CrownPath-compatible HMAC hashes.

Not wired to production. Caller must validate signed JWT, Owner, MFA, and CSRF.
"""
import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def consume_hmac_session_proof_test(engine, *, token, user_id, session_id,
                                    secret, now=None):
    if not all(isinstance(v, str) and v.strip() for v in
               (token, user_id, session_id, secret)):
        return False
    when = datetime.now(timezone.utc) if now is None else now
    proof_hash = hashlib.sha256(token.encode()).hexdigest()
    session_hash = hmac.new(secret.encode(), f"session:{session_id}".encode(),
                            hashlib.sha256).hexdigest()
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
            """), dict(timestamp=int(when.timestamp()), when=when,
                       proof_hash=proof_hash, session_hash=session_hash,
                       user_id=user_id, session_id=session_id))
            return result.rowcount == 1
