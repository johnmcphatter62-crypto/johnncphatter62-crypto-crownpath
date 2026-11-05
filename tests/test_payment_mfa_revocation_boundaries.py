"""Disposable SQLite tests for payment MFA revocation identity boundaries."""
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof, revoke_session_proofs,
)

def test_revocation_is_scoped_to_both_user_and_session(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'identity.db'}")
    try:
        create_test_schema(engine)
        first = issue_verified_proof(engine, user_id="owner-a", session_id="shared-id", now=100)
        second = issue_verified_proof(engine, user_id="owner-b", session_id="shared-id", now=100)
        assert revoke_session_proofs(engine, user_id="owner-a", session_id="shared-id", now=101) == 1
        assert not consume_proof(engine, token=first, user_id="owner-a", session_id="shared-id", now=102)
        assert consume_proof(engine, token=second, user_id="owner-b", session_id="shared-id", now=102)
    finally:
        engine.dispose()

def test_revocation_is_idempotent(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'idempotent.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="session", now=100)
        assert revoke_session_proofs(engine, user_id="owner", session_id="session", now=101) == 1
        assert revoke_session_proofs(engine, user_id="owner", session_id="session", now=102) == 0
        assert not consume_proof(engine, token=proof, user_id="owner", session_id="session", now=103)
    finally:
        engine.dispose()
