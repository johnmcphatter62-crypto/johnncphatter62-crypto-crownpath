"""Proof consumption must fail closed on malformed trusted-verification flags."""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("field,value", [
    ("csrf_verified", None), ("csrf_verified", 1), ("csrf_verified", "true"),
    ("session_active", None), ("session_active", 1), ("session_active", "true"),
])
def test_non_boolean_trust_flags_do_not_consume_proof(tmp_path, field, value):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'flag.db'}")
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        args = dict(user=OWNER, session_id="s1", proof_token=token,
                    csrf_verified=True, session_active=True, now=101)
        args[field] = value
        assert not authorize_and_consume_payment_proof(engine, **args)
        args[field] = True
        assert authorize_and_consume_payment_proof(engine, **args)
    finally:
        engine.dispose()
