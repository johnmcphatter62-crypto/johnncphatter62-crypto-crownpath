"""Malformed proof tokens must fail closed without consuming a valid proof."""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("bad_token", [None, "", 1, True, [], {}, "not-a-valid-token"])
def test_malformed_proof_token_does_not_consume_valid_proof(tmp_path, bad_token):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'bad_token.db'}")
    try:
        create_test_schema(engine)
        good = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        args = dict(user=OWNER, session_id="s1", csrf_verified=True, session_active=True, now=101)
        assert not authorize_and_consume_payment_proof(engine, proof_token=bad_token, **args)
        assert authorize_and_consume_payment_proof(engine, proof_token=good, **args)
    finally:
        engine.dispose()
