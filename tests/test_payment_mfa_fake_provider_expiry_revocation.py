"""Verify no fake payment-provider call follows expired or revoked proofs.

This is test-only orchestration; it is not an HTTP route or live provider.
"""
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, revoke_session_proofs,
)
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof


OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}


def test_expired_and_revoked_proofs_never_reach_fake_provider(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'revoked_provider.db'}")
    calls = []
    try:
        create_test_schema(engine)
        expired = issue_verified_proof(
            engine, user_id="owner", session_id="old", now=100, ttl_seconds=2
        )
        revoked = issue_verified_proof(
            engine, user_id="owner", session_id="current", now=100
        )
        assert revoke_session_proofs(
            engine, user_id="owner", session_id="current", now=101
        ) == 1

        for session_id, token in [("old", expired), ("current", revoked)]:
            allowed = authorize_and_consume_payment_proof(
                engine, user=OWNER, session_id=session_id, proof_token=token,
                csrf_verified=True, session_active=True, now=103,
            )
            if allowed:
                calls.append("fake-provider-configure")
            assert not allowed

        assert calls == []
    finally:
        engine.dispose()
