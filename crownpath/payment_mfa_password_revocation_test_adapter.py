"""Test-only password-change revocation in one disposable DB transaction.

Not wired to live authentication or payments. Caller must authenticate the Owner.
"""
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.orm import Session
from crownpath.models import AuthToken, User


def revoke_password_sessions_and_proofs_test(engine, *, user_id, new_hash,
                                             now=None, fail_midway=False):
    if not isinstance(user_id, str) or not user_id.strip():
        return False
    if not isinstance(new_hash, str) or not new_hash.strip():
        return False
    when = datetime.now(timezone.utc) if now is None else now
    with Session(engine) as db:
        with db.begin():
            owner = db.get(User, user_id)
            if owner is None or not owner.active or owner.role != "OWNER":
                return False
            owner.password_hash = new_hash
            db.execute(sa.update(AuthToken).where(
                AuthToken.user_id == user_id,
                AuthToken.token_type == "SESSION",
                AuthToken.used_at.is_(None),
            ).values(used_at=when))
            if fail_midway:
                raise RuntimeError("synthetic failure before proof revocation")
            db.execute(sa.text(
                "UPDATE payment_mfa_proofs_test SET used_at = :ts "
                "WHERE user_id = :uid AND used_at IS NULL"
            ), {"ts": int(when.timestamp()), "uid": user_id})
    return True
