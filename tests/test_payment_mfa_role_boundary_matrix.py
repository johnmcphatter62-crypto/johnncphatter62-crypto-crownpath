"""Test-only policy matrix for payment MFA proof boundaries.

These cases are isolated helper tests, not live route or MFA verification tests.
"""
import pytest
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_issue_policy import may_issue_payment_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("role", ["STUDENT", "INSTRUCTOR", "ADMIN", "", None])
def test_other_roles_cannot_issue_or_consume(tmp_path, role):
    user = dict(OWNER, role=role)
    assert not may_issue_payment_proof(
        user, server_verified_mfa=True, session_id="session",
        csrf_verified=True,
    )
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'roles.db'}")
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="session", now=100)
        kwargs = dict(session_id="session", proof_token=token, csrf_verified=True,
                      session_active=True, now=101)
        assert not authorize_and_consume_payment_proof(engine, user=user, **kwargs)
        assert authorize_and_consume_payment_proof(engine, user=OWNER, **kwargs)
    finally:
        engine.dispose()
