"""Inactive and MFA-unenrolled owner records cannot authorize payment MFA proofs."""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_issue_policy import may_issue_payment_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("field,value", [
    ("active", False), ("active", None),
    ("mfa_enabled", False), ("mfa_enabled", None),
])
def test_ineligible_owner_cannot_issue_or_consume(tmp_path, field, value):
    user = dict(OWNER, **{field: value})
    assert not may_issue_payment_proof(
        user, server_verified_mfa=True, session_id="session",
        csrf_verified=True,
    )
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'owner_eligibility.db'}")
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="session", now=100)
        kwargs = dict(session_id="session", proof_token=token,
                      csrf_verified=True, session_active=True, now=101)
        assert not authorize_and_consume_payment_proof(engine, user=user, **kwargs)
        assert authorize_and_consume_payment_proof(engine, user=OWNER, **kwargs)
    finally:
        engine.dispose()
