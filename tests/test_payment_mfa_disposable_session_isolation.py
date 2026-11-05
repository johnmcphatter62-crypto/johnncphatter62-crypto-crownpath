"""Disposable SQLite test for session revocation with multiple sessions.

No application or production authentication database is accessed.
"""
import sqlalchemy as sa
from crownpath.payment_mfa_disposable_session_store import (
    create_session_test_schema, add_test_session,
    is_active_test_session, revoke_test_session,
)


def test_revoking_one_session_preserves_other_session(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'two_sessions.db'}")
    try:
        create_session_test_schema(engine)
        add_test_session(engine, user_id="owner", session_id="session-a")
        add_test_session(engine, user_id="owner", session_id="session-b")
        add_test_session(engine, user_id="other-owner", session_id="session-a")

        assert revoke_test_session(engine, user_id="owner", session_id="session-a")
        assert not is_active_test_session(engine, "owner", "session-a")
        assert is_active_test_session(engine, "owner", "session-b")
        assert is_active_test_session(engine, "other-owner", "session-a")
    finally:
        engine.dispose()
