"""Disposable database tests for session-scoped payment MFA proof revocation."""
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof, revoke_session_proofs,
)

def test_revoking_session_invalidates_its_unused_proofs_only(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'revoke.db'}")
    try:
        create_test_schema(engine)
        old = issue_verified_proof(engine, user_id="owner", session_id="old", now=100)
        other = issue_verified_proof(engine, user_id="owner", session_id="other", now=100)
        assert revoke_session_proofs(engine, user_id="owner", session_id="old", now=101) == 1
        assert not consume_proof(engine, token=old, user_id="owner", session_id="old", now=102)
        assert consume_proof(engine, token=other, user_id="owner", session_id="other", now=102)
    finally:
        engine.dispose()

def test_revocation_fails_closed_for_missing_identity(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'missing.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="old", now=100)
        assert revoke_session_proofs(engine, user_id="", session_id="old", now=101) == 0
        assert revoke_session_proofs(engine, user_id="owner", session_id="", now=101) == 0
        assert consume_proof(engine, token=proof, user_id="owner", session_id="old", now=102)
    finally:
        engine.dispose()
