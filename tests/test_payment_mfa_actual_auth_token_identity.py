"""Actual ORM: another owner's session cannot authenticate this owner."""
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session


def test_auth_token_user_binding(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'auth_identity.db'}")
    try:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            for user_id in ("owner-a", "owner-b"):
                db.add(User(
                    user_id=user_id, name=user_id,
                    email=f"{user_id}@example.invalid",
                    password_hash="synthetic-only", role="OWNER",
                    active=True, mfa_enabled=True,
                ))
            db.add(AuthToken(
                token_id="IDENTITY-TOKEN", user_id="owner-b",
                token_hash=hashlib.sha256(b"owner-b-jti").hexdigest(),
                token_type="SESSION", expires_at=now + timedelta(minutes=10),
                created_at=now,
            ))
            db.commit()

        def active_session(user_id, session_id):
            with Session(engine) as db:
                record = db.scalar(sa.select(AuthToken).where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_hash == hashlib.sha256(session_id.encode()).hexdigest(),
                    AuthToken.token_type == "SESSION",
                    AuthToken.used_at.is_(None),
                ))
                return bool(record and record.expires_at.replace(
                    tzinfo=timezone.utc
                ) > datetime.now(timezone.utc))

        def active_user(user_id):
            with Session(engine) as db:
                user = db.get(User, user_id)
                return bool(user and user.active)

        forged_identity_claim = jwt.encode({
            "sub": "owner-a", "jti": "owner-b-jti", "purpose": "session",
            "exp": now + timedelta(minutes=5),
        }, "synthetic-secret", algorithm="HS256")
        assert validate_signed_session(
            forged_identity_claim, secret="synthetic-secret", algorithm="HS256",
            active_session=active_session, active_user=active_user,
        ) is None
    finally:
        engine.dispose()
