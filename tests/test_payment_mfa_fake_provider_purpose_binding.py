"""Reject fake payment-provider changes when proof purpose is incorrect.

All credentials, identities and sessions are synthetic; no live route is used.
"""
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}


def test_wrong_purpose_proof_cannot_trigger_fake_provider(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'purpose.db'}")
    provider_changes = []
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="session-a", now=100)
        digest = __import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
        with engine.begin() as connection:
            connection.execute(
                sa.text("UPDATE payment_mfa_proofs_test SET purpose = :purpose WHERE proof_hash = :digest"),
                {"purpose": "profile.edit", "digest": digest},
            )
        allowed = authorize_and_consume_payment_proof(
            engine, user=OWNER, session_id="session-a", proof_token=token,
            csrf_verified=True, session_active=True, now=101,
        )
        if allowed:
            provider_changes.append("configured")
        assert not allowed
        assert provider_changes == []
    finally:
        engine.dispose()
