"""Malformed owner data must fail closed at the consumption boundary."""
import pytest
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

VALID = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("user", [
    None,
    {},
    {"role": "OWNER", "active": True, "mfa_enabled": True},
    {"user_id": "", "role": "OWNER", "active": True, "mfa_enabled": True},
    {"user_id": None, "role": "OWNER", "active": True, "mfa_enabled": True},
])
def test_missing_owner_identity_never_consumes_proof(tmp_path, user):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'missing_owner.db'}")
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        assert not authorize_and_consume_payment_proof(
            engine, user=user, session_id="s1", proof_token=token,
            csrf_verified=True, session_active=True, now=101,
        )
        assert authorize_and_consume_payment_proof(
            engine, user=VALID, session_id="s1", proof_token=token,
            csrf_verified=True, session_active=True, now=101,
        )
    finally:
        engine.dispose()
