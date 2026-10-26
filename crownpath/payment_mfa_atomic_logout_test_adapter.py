"""Test-only atomic logout and proof revocation using actual AuthToken ORM.

Not integrated into live logout routes. Both updates use one disposable SQLite
transaction, so an exception rolls back both state changes.
"""
import hashlib
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.models import AuthToken


def revoke_session_and_proofs_test(engine, *, user_id, session_id, now=None,
                                   fail_after_session_update=False):
    """Atomically revoke a matching active session and its unused proofs.

    Return False if the session was not active. The caller must independently
    validate the signed session and derive user_id/jti from verified claims.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        return False
    if not isinstance(session_id, str) or not session_id.strip():
        return False
    when = datetime.now(timezone.utc) if now is None else now
    proof_timestamp = int(when.timestamp())
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    with Session(engine) as db:
        with db.begin():
            result = db.execute(
                sa.update(AuthToken)
                .where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_hash == digest,
                    AuthToken.token_type == "SESSION",
                    AuthToken.used_at.is_(None),
                    AuthToken.expires_at > when,
                )
                .values(used_at=when)
            )
            if result.rowcount != 1:
                return False
            if fail_after_session_update:
                raise RuntimeError("synthetic failure between revocations")
            db.execute(sa.text("""
                UPDATE payment_mfa_proofs_test SET used_at = :now
                WHERE user_id = :user_id AND session_id = :session_id
                  AND used_at IS NULL
            """), {"now": proof_timestamp, "user_id": user_id,
                   "session_id": session_id})
    return True
