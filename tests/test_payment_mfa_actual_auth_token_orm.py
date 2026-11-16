"""Verify the signed-session adapter against actual CrownPath ORM tables.

Uses only a disposable SQLite engine and a synthetic signing key.
"""
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session


def test_actual_auth_token_orm_revocation(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'actual_models.db'}")
    try:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(
                user_id="owner", name="Test Owner", email="owner@example.invalid",
                password_hash="synthetic-not-a-real-password", role="OWNER",
                active=True, mfa_enabled=True,
            ))
            db.add(AuthToken(
                token_id="TEST-TOKEN-1", user_id="owner",
                token_hash=hashlib.sha256(b"synthetic-jti").hexdigest(),
                token_type="SESSION", expires_at=now + timedelta(minutes=10),
                created_at=now,
            ))
            db.commit()

        token = jwt.encode({
            "sub": "owner", "jti": "synthetic-jti", "purpose": "session",
            "exp": now + timedelta(minutes=5),
        }, "disposable-test-signing-key", algorithm="HS256")

        def active_session(user_id, session_id):
            with Session(engine) as db:
                record = db.scalar(sa.select(AuthToken).where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_hash == hashlib.sha256(session_id.encode()).hexdigest(),
                    AuthToken.token_type == "SESSION",
                    AuthToken.used_at.is_(None),
                ))
                if record is None:
                    return False
                expiry = record.expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                return expiry > datetime.now(timezone.utc)

        def active_user(user_id):
            with Session(engine) as db:
                record = db.get(User, user_id)
                return bool(record is not None and record.active)

        def validate():
            return validate_signed_session(
                token, secret="disposable-test-signing-key", algorithm="HS256",
                active_session=active_session, active_user=active_user,
            )

        assert validate() == {"user_id": "owner", "session_id": "synthetic-jti"}
        with Session(engine) as db:
            record = db.get(AuthToken, "TEST-TOKEN-1")
            record.used_at = datetime.now(timezone.utc)
            db.commit()
        assert validate() is None
    finally:
        engine.dispose()
