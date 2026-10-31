"""Actual CrownPath auth lifecycle in an isolated SQLite database.

Monkeypatches the auth module's session factory and signing key; never opens
an application-configured database connection or uses live credentials.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User
import crownpath.auth as auth


def test_actual_auth_create_decode_revoke(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth_lifecycle.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="test-owner", name="Test Owner",
                email="lifecycle-owner@example.invalid",
                password_hash="synthetic-only", role="OWNER",
                active=True, mfa_enabled=True,
            ))
            db.commit()

        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "isolated-test-key-not-production")
        token = auth.create_access_token("test-owner")
        assert auth.decode_access_token(token) == "test-owner"
        assert auth.revoke_access_token(token) is True
        assert auth.decode_access_token(token) is None
        assert auth.revoke_access_token(token) is False
    finally:
        engine.dispose()
