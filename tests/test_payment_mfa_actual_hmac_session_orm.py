"""Isolated actual-ORM signed session tests using CrownPath's HMAC hash format.

Disposable SQLite, synthetic signing key; no application database or payment route.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_session_context import verified_session_context
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session


SECRET = "synthetic-hmac-secret-for-tests"


def _hash_session_id(jti):
    return hmac.new(SECRET.encode(), f"session:{jti}".encode(), hashlib.sha256).hexdigest()


def test_actual_orm_hmac_session_validation_and_revocation(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'hmac_auth.db'}")
    try:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(
                user_id="owner-a", name="Synthetic Owner",
                email="owner-a@example.invalid", password_hash="synthetic-only",
                role="OWNER", active=True, mfa_enabled=True,
            ))
            db.add(AuthToken(
                token_id="HMAC-TEST-TOKEN", user_id="owner-a",
                token_hash=_hash_session_id("owner-a-jti"),
                token_type="SESSION", expires_at=now + timedelta(minutes=10),
                created_at=now,
            ))
            db.commit()

        def active_session(user_id, session_id):
            with Session(engine) as db:
                row = db.scalar(sa.select(AuthToken).where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_hash == _hash_session_id(session_id),
                    AuthToken.token_type == "SESSION",
                    AuthToken.used_at.is_(None),
                ))
                if row is None:
                    return False
                expiry = row.expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                return expiry > datetime.now(timezone.utc)

        def active_user(user_id):
            with Session(engine) as db:
                user = db.get(User, user_id)
                return bool(user and user.active and user.role == "OWNER")

        def validate(token):
            return verified_session_context(
                token,
                decode_and_check=lambda signed: validate_signed_session(
                    signed, secret=SECRET, algorithm="HS256",
                    active_session=active_session, active_user=active_user,
                ),
            )

        def signed(sub="owner-a", jti="owner-a-jti", *, secret=SECRET, purpose="session", expiry=None):
            return jwt.encode({
                "sub": sub, "jti": jti, "purpose": purpose,
                "exp": expiry if expiry is not None else now + timedelta(minutes=5),
            }, secret, algorithm="HS256")

        valid = signed()
        assert validate(valid) == ("owner-a", "owner-a-jti")
        assert validate(signed(secret="forged-signing-key")) is None
        assert validate(signed(expiry=now - timedelta(minutes=1))) is None
        assert validate(signed(purpose="mfa_challenge")) is None
        assert validate(signed(sub="another-owner")) is None
        assert validate(signed(jti="unregistered-jti")) is None
        with Session(engine) as db:
            row = db.get(AuthToken, "HMAC-TEST-TOKEN")
            row.used_at = datetime.now(timezone.utc)
            db.commit()
        assert validate(valid) is None

        # Reissue a separate, still-valid session for an Owner whose account
        # is subsequently disabled. Account status must independently deny.
        with Session(engine) as db:
            db.add(AuthToken(
                token_id="HMAC-TEST-TOKEN-2", user_id="owner-a",
                token_hash=_hash_session_id("owner-a-new-jti"),
                token_type="SESSION", expires_at=now + timedelta(minutes=10),
                created_at=now,
            ))
            db.commit()
        replacement = signed(jti="owner-a-new-jti")
        assert validate(replacement) == ("owner-a", "owner-a-new-jti")
        with Session(engine) as db:
            owner = db.get(User, "owner-a")
            owner.active = False
            db.commit()
        assert validate(replacement) is None

        # A newly issued, otherwise-valid session must also fail after the
        # Owner's role changes away from OWNER, even while account is active.
        with Session(engine) as db:
            owner = db.get(User, "owner-a")
            owner.active = True
            db.add(AuthToken(
                token_id="HMAC-TEST-TOKEN-3", user_id="owner-a",
                token_hash=_hash_session_id("owner-a-role-jti"),
                token_type="SESSION", expires_at=now + timedelta(minutes=10),
                created_at=now,
            ))
            db.commit()
        role_token = signed(jti="owner-a-role-jti")
        assert validate(role_token) == ("owner-a", "owner-a-role-jti")
        with Session(engine) as db:
            owner = db.get(User, "owner-a")
            owner.role = "LEARNER"
            db.commit()
        assert validate(role_token) is None
    finally:
        engine.dispose()
