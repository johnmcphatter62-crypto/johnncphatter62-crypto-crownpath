"""Payment MFA fake-provider boundary: reject cross-session and cross-owner proofs.

No production routes or provider credentials are used.
"""
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}
OTHER_OWNER = {"user_id": "other-owner", "role": "OWNER", "active": True, "mfa_enabled": True}


def test_wrong_owner_and_session_cannot_trigger_provider(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'owner_session.db'}")
    provider_calls = []
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="session-a", now=100)

        for user, session in [(OTHER_OWNER, "session-a"), (OWNER, "session-b")]:
            allowed = authorize_and_consume_payment_proof(
                engine, user=user, session_id=session, proof_token=proof,
                csrf_verified=True, session_active=True, now=101,
            )
            if allowed:
                provider_calls.append("configured")
            assert not allowed

        assert provider_calls == []
        assert authorize_and_consume_payment_proof(
            engine, user=OWNER, session_id="session-a", proof_token=proof,
            csrf_verified=True, session_active=True, now=101,
        )
        provider_calls.append("configured")
        assert provider_calls == ["configured"]
    finally:
        engine.dispose()
