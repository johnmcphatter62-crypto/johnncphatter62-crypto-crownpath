"""Non-dictionary user identities must fail closed at both payment MFA policy boundaries."""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_issue_policy import may_issue_payment_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("bad_user", ["owner", 123, True, [], ["owner"], object()])
def test_invalid_user_shape_denied_by_both_guards(tmp_path, bad_user):
    assert not may_issue_payment_proof(
        bad_user, server_verified_mfa=True, session_id="s1", csrf_verified=True
    )
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'bad_user.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        args = dict(session_id="s1", proof_token=proof, csrf_verified=True,
                    session_active=True, now=101)
        assert not authorize_and_consume_payment_proof(engine, user=bad_user, **args)
        assert authorize_and_consume_payment_proof(engine, user=OWNER, **args)
    finally:
        engine.dispose()
