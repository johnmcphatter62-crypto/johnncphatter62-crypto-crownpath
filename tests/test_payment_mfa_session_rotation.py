"""Isolated login-session rotation tests for payment MFA proofs.

No live authentication service, provider, or production database is accessed.
"""
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof,
)

def test_new_login_session_cannot_reuse_prior_session_proof(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'session_rotation.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="old-session", now=100)
        assert not consume_proof(engine, token=proof, user_id="owner", session_id="new-session", now=101)
        assert consume_proof(engine, token=proof, user_id="owner", session_id="old-session", now=101)
    finally:
        engine.dispose()

def test_two_sessions_have_independent_proofs(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'independent.db'}")
    try:
        create_test_schema(engine)
        first = issue_verified_proof(engine, user_id="owner", session_id="session-a", now=100)
        second = issue_verified_proof(engine, user_id="owner", session_id="session-b", now=100)
        assert not consume_proof(engine, token=first, user_id="owner", session_id="session-b", now=101)
        assert consume_proof(engine, token=second, user_id="owner", session_id="session-b", now=101)
        assert consume_proof(engine, token=first, user_id="owner", session_id="session-a", now=101)
    finally:
        engine.dispose()
