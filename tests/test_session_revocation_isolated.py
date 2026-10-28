"""Synthetic session revocation checks using disposable SQLite only."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.auth as auth
from crownpath.db_engine import Base
from crownpath.models import User


def test_logout_and_account_changes_revoke_sessions(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic_sessions.db'}")
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-session-revocation-key")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-learner-session",
                name="Synthetic Session Learner",
                email="session-learner@example.com",
                password_hash=auth.hash_password("SyntheticPassword!2026"),
                role="COSMETOLOGY_PRO",
                active=True,
            ))
            db.commit()

        first = auth.create_access_token("synthetic-learner-session")
        assert auth.decode_access_token(first) == "synthetic-learner-session"
        assert auth.revoke_access_token(first) is True
        assert auth.decode_access_token(first) is None
        assert auth.revoke_access_token(first) is False

        second = auth.create_access_token("synthetic-learner-session")
        assert auth.decode_access_token(second) == "synthetic-learner-session"
        auth.set_user_role("synthetic-learner-session", "BARBER")
        assert auth.decode_access_token(second) is None

        third = auth.create_access_token("synthetic-learner-session")
        assert auth.decode_access_token(third) == "synthetic-learner-session"
        auth.set_user_active("synthetic-learner-session", False)
        assert auth.decode_access_token(third) is None
        user, status = auth.authenticate(
            "session-learner@example.com", "SyntheticPassword!2026"
        )
        assert user is None and status == "INVALID"
    finally:
        engine.dispose()
