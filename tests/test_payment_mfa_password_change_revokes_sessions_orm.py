"""Disposable ORM regression: password change revokes all Owner sessions only.

Mirrors the AuthToken update in crownpath.auth.update_password without calling
application-configured database or changing any real credentials.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session
from crownpath.payment_mfa_session_context import verified_session_context

SECRET = "synthetic-password-change-session-secret"


def _hash_jti(jti):
    return hmac.new(SECRET.encode(), f"session:{jti}".encode(), hashlib.sha256).hexdigest()


def test_password_change_revokes_all_owner_sessions_but_not_other_user(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'password_change.db'}")
    try:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            for uid in ("owner-a", "owner-b"):
                db.add(User(user_id=uid, name=uid, email=f"{uid}@example.invalid",
                            password_hash="synthetic-before", role="OWNER",
                            active=True, mfa_enabled=True))
            for tid, uid, jti in (
                ("SESSION-A1", "owner-a", "a-one"),
                ("SESSION-A2", "owner-a", "a-two"),
                ("SESSION-B1", "owner-b", "b-one"),
            ):
                db.add(AuthToken(token_id=tid, user_id=uid, token_hash=_hash_jti(jti),
                                 token_type="SESSION", expires_at=now + timedelta(minutes=10),
                                 created_at=now))
            db.commit()

        def active_session(uid, jti):
            with Session(engine) as db:
                row = db.scalar(sa.select(AuthToken).where(
                    AuthToken.user_id == uid,
                    AuthToken.token_hash == _hash_jti(jti),
                    AuthToken.token_type == "SESSION",
                    AuthToken.used_at.is_(None),
                ))
                if row is None:
                    return False
                expires = row.expires_at
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                return expires > datetime.now(timezone.utc)

        def active_owner(uid):
            with Session(engine) as db:
                user = db.get(User, uid)
                return bool(user and user.active and user.role == "OWNER")

        def token(uid, jti):
            return jwt.encode({"sub": uid, "jti": jti, "purpose": "session",
                               "exp": now + timedelta(minutes=5)}, SECRET, algorithm="HS256")

        def check(signed):
            return verified_session_context(signed, decode_and_check=lambda t:
                validate_signed_session(t, secret=SECRET, algorithm="HS256",
                                        active_session=active_session, active_user=active_owner))

        a1, a2, b1 = token("owner-a", "a-one"), token("owner-a", "a-two"), token("owner-b", "b-one")
        assert check(a1) == ("owner-a", "a-one")
        assert check(a2) == ("owner-a", "a-two")
        assert check(b1) == ("owner-b", "b-one")

        # Same scoped ORM update as auth.update_password; no real passwords used.
        with Session(engine) as db:
            owner = db.get(User, "owner-a")
            owner.password_hash = "synthetic-after"
            result = db.execute(sa.update(AuthToken).where(
                AuthToken.user_id == "owner-a",
                AuthToken.token_type == "SESSION",
                AuthToken.used_at.is_(None),
            ).values(used_at=datetime.now(timezone.utc)))
            assert result.rowcount == 2
            db.commit()

        assert check(a1) is None
        assert check(a2) is None
        assert check(b1) == ("owner-b", "b-one")
    finally:
        engine.dispose()
