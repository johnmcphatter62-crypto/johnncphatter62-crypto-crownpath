"""SQLite-only session row tests; no production database accessed."""
import sqlalchemy as sa
from crownpath.payment_mfa_disposable_session_store import (
    create_session_test_schema, add_test_session,
    is_active_test_session, revoke_test_session,
)
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session
import jwt
from datetime import datetime, timedelta, timezone


def test_signed_session_requires_matching_unrevoked_database_row(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'sessions.db'}")
    try:
        create_session_test_schema(engine)
        add_test_session(engine, user_id="owner", session_id="s1")
        token = jwt.encode({
            "sub": "owner", "jti": "s1", "purpose": "session",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }, "test-secret", algorithm="HS256")

        def check():
            return validate_signed_session(
                token, secret="test-secret", algorithm="HS256",
                active_session=lambda u, s: is_active_test_session(engine, u, s),
                active_user=lambda u: u == "owner",
            )

        assert check() == {"user_id": "owner", "session_id": "s1"}
        assert not is_active_test_session(engine, "other", "s1")
        assert not is_active_test_session(engine, "owner", "wrong")
        assert revoke_test_session(engine, user_id="owner", session_id="s1")
        assert check() is None
        assert not revoke_test_session(engine, user_id="owner", session_id="s1")
    finally:
        engine.dispose()
