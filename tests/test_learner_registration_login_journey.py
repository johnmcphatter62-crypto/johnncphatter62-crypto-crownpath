"""Disposable learner registration, login, and session lifecycle smoke test.

Uses only synthetic identity data and an isolated SQLite database. Does not
enable enrollment flags or touch a live CrownPath account.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.auth as auth
from crownpath.db_engine import Base


def test_learner_register_login_and_logout(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'learner_journey.db'}")
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "disposable-learner-test-secret")

        learner = auth.create_user(
            "Synthetic Learner", "learner-journey@example.invalid",
            "SyntheticPassword!2026", "COSMETOLOGY_PRO",
        )
        assert learner["role"] == "COSMETOLOGY_PRO"
        assert learner["email"] == "learner-journey@example.invalid"

        logged_in, status = auth.authenticate(
            "learner-journey@example.invalid", "SyntheticPassword!2026"
        )
        assert status == "OK"
        assert logged_in["user_id"] == learner["user_id"]

        token = auth.create_access_token(learner["user_id"])
        assert auth.decode_access_token(token) == learner["user_id"]
        assert auth.revoke_access_token(token) is True
        assert auth.decode_access_token(token) is None

        with pytest.raises(ValueError, match="self-assigned"):
            auth.create_user(
                "Unauthorized Owner", "fake-owner@example.invalid",
                "SyntheticPassword!2026", "OWNER",
            )
    finally:
        engine.dispose()
