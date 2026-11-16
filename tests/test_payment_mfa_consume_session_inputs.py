"""Reject invalid session identifiers before proof consumption without consuming a good proof."""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("session_id", [None, "", "   ", 1, True, [], {}, "other-session"])
def test_bad_session_never_consumes_proof(tmp_path, session_id):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'bad_session.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="trusted-session", now=100)
        args = dict(user=OWNER, proof_token=proof, csrf_verified=True,
                    session_active=True, now=101)
        assert not authorize_and_consume_payment_proof(
            engine, session_id=session_id, **args
        )
        assert authorize_and_consume_payment_proof(
            engine, session_id="trusted-session", **args
        )
        assert not authorize_and_consume_payment_proof(
            engine, session_id="trusted-session", **args
        )
    finally:
        engine.dispose()
