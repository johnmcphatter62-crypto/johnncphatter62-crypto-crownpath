"""Isolated synthetic MFA recovery and account-lockout regression tests."""
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.auth as auth
from crownpath.db_engine import Base
from crownpath.models import User


def test_recovery_code_is_one_time_and_user_bound(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic_mfa.db'}")
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            for user_id in ("synthetic-a", "synthetic-b"):
                db.add(User(
                    user_id=user_id, name=user_id,
                    email=f"{user_id}@example.invalid",
                    password_hash=auth.hash_password("SyntheticPassword!2026"),
                    role="COSMETOLOGY_PRO", active=True,
                ))
            db.commit()
        code = auth.generate_mfa_recovery_codes("synthetic-a", count=1)[0]
        assert auth.consume_mfa_recovery_code("synthetic-b", code) is False
        assert auth.consume_mfa_recovery_code("synthetic-a", code) is True
        assert auth.consume_mfa_recovery_code("synthetic-a", code) is False
    finally:
        engine.dispose()


def test_login_lockout_blocks_correct_password_until_expiry(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic_lockout.db'}")
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-lockout", name="Synthetic Lockout",
                email="synthetic-lockout@example.invalid",
                password_hash=auth.hash_password("SyntheticPassword!2026"),
                role="COSMETOLOGY_PRO", active=True,
            ))
            db.commit()
        for _ in range(auth.MAX_FAILED_ATTEMPTS):
            user, status = auth.authenticate(
                "synthetic-lockout@example.invalid", "IncorrectSyntheticPassword"
            )
            assert user is None and status == "INVALID"
        user, status = auth.authenticate(
            "synthetic-lockout@example.invalid", "SyntheticPassword!2026"
        )
        assert user is None and status == "LOCKED"
        with Session(engine) as db:
            row = db.get(User, "synthetic-lockout")
            row.locked_until = auth.now_utc() - timedelta(minutes=1)
            db.commit()
        user, status = auth.authenticate(
            "synthetic-lockout@example.invalid", "SyntheticPassword!2026"
        )
        assert status == "OK" and user["user_id"] == "synthetic-lockout"
    finally:
        engine.dispose()
