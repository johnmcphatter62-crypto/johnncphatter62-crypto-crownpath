"""Isolated consumption policy tests with disposable SQLite."""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("overrides", [
    {"csrf_verified": False}, {"csrf_verified": "true"},
    {"session_active": False}, {"session_active": "true"},
    {"session_id": ""}, {"session_id": "other"},
    {"proof_token": ""},
    {"user": {"user_id": "student", "role": "STUDENT", "active": True, "mfa_enabled": True}},
])
def test_guard_rejects_invalid_inputs_without_consuming(tmp_path, overrides):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'policy.db'}")
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        args = dict(user=OWNER, session_id="s1", proof_token=token,
                    csrf_verified=True, session_active=True, now=101)
        args.update(overrides)
        assert not authorize_and_consume_payment_proof(engine, **args)
        assert authorize_and_consume_payment_proof(engine, user=OWNER, session_id="s1",
            proof_token=token, csrf_verified=True, session_active=True, now=101)
        assert not authorize_and_consume_payment_proof(engine, user=OWNER, session_id="s1",
            proof_token=token, csrf_verified=True, session_active=True, now=102)
    finally:
        engine.dispose()
