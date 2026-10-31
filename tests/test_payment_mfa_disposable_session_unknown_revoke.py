"""Disposable session isolation: unknown revocations cannot affect valid sessions."""
import sqlalchemy as sa
from crownpath.payment_mfa_disposable_session_store import (
    create_session_test_schema, add_test_session,
    is_active_test_session, revoke_test_session,
)


def test_unknown_session_revocation_preserves_real_session(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'unknown_revocation.db'}")
    try:
        create_session_test_schema(engine)
        add_test_session(engine, user_id="owner", session_id="real-session")
        assert not revoke_test_session(
            engine, user_id="owner", session_id="unknown-session"
        )
        assert not revoke_test_session(
            engine, user_id="other-owner", session_id="real-session"
        )
        assert is_active_test_session(engine, "owner", "real-session")
    finally:
        engine.dispose()
