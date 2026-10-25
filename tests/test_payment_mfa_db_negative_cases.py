"""Fail-closed proof checks on disposable SQLite database only."""
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof,
)

def test_wrong_purpose_does_not_consume_and_correct_purpose_still_works(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'purpose.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        assert not consume_proof(engine, token=proof, user_id="owner", session_id="s1", purpose="users.manage", now=101)
        assert consume_proof(engine, token=proof, user_id="owner", session_id="s1", now=101)
    finally:
        engine.dispose()

def test_missing_session_and_token_fail_closed(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'missing.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        assert not consume_proof(engine, token=proof, user_id="owner", session_id="", now=101)
        assert not consume_proof(engine, token="", user_id="owner", session_id="s1", now=101)
        assert consume_proof(engine, token=proof, user_id="owner", session_id="s1", now=101)
    finally:
        engine.dispose()
