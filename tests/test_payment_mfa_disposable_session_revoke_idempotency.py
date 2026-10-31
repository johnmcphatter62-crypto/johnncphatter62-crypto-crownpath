"""Disposable session store: revocation is idempotent and remains denied."""
import sqlalchemy as sa
from crownpath.payment_mfa_disposable_session_store import (
    create_session_test_schema, add_test_session,
    is_active_test_session, revoke_test_session,
)


def test_repeated_revocation_never_reactivates_session(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'revoke_twice.db'}")
    try:
        create_session_test_schema(engine)
        add_test_session(engine, user_id="owner", session_id="s1")
        assert is_active_test_session(engine, "owner", "s1")
        assert revoke_test_session(engine, user_id="owner", session_id="s1")
        for _ in range(3):
            assert not revoke_test_session(engine, user_id="owner", session_id="s1")
            assert not is_active_test_session(engine, "owner", "s1")
    finally:
        engine.dispose()
