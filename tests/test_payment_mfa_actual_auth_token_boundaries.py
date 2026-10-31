"""Actual AuthToken ORM boundary cases in a disposable SQLite database."""
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session


def test_actual_orm_expired_session_and_disabled_owner_fail_closed(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'auth_boundaries.db'}")
    try:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(
                user_id="owner", name="Owner", email="owner-boundary@example.invalid",
                password_hash="synthetic-only", role="OWNER", active=True,
                mfa_enabled=True,
            ))
            db.add(AuthToken(
                token_id="BOUNDARY-TOKEN", user_id="owner",
                token_hash=hashlib.sha256(b"test-jti").hexdigest(),
                token_type="SESSION", expires_at=now - timedelta(seconds=1),
                created_at=now - timedelta(minutes=20),
            ))
            db.commit()

        token = jwt.encode({
            "sub": "owner", "jti": "test-jti", "purpose": "session",
            "exp": now + timedelta(minutes=5),
        }, "test-signing-secret", algorithm="HS256")

        def active_session(user_id, session_id):
            with Session(engine) as db:
                row = db.scalar(sa.select(AuthToken).where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_hash == hashlib.sha256(session_id.encode()).hexdigest(),
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
                return bool(user and user.active)

        def check():
            return validate_signed_session(
                token, secret="test-signing-secret", algorithm="HS256",
                active_session=active_session, active_user=active_user,
            )

        assert check() is None  # JWT valid but AuthToken DB expiry elapsed.
        with Session(engine) as db:
            row = db.get(AuthToken, "BOUNDARY-TOKEN")
            row.expires_at = now + timedelta(minutes=10)
            db.commit()
        assert check() == {"user_id": "owner", "session_id": "test-jti"}
        with Session(engine) as db:
            user = db.get(User, "owner")
            user.active = False
            db.commit()
        assert check() is None
    finally:
        engine.dispose()
