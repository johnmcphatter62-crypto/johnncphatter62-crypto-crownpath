"""Disposable fake-provider acceptance checks for payment MFA authorization.

No HTTP endpoint, live provider, real sessions, or production DB are involved.
"""
import pytest
import sqlalchemy as sa
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_consume_policy import authorize_and_consume_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}
LEARNER = {"user_id": "learner", "role": "HOME_CARE", "active": True, "mfa_enabled": True}

class FakeProvider:
    def __init__(self):
        self.changes = []

    def configure(self, destination):
        self.changes.append(destination)


def simulated_payment_request(engine, provider, *, user, session_id, proof,
                              csrf_verified, session_active, destination):
    # Test-only orchestration: the caller supplies already-verified assertions.
    # This does NOT verify actual cookies, MFA codes, or CSRF tokens.
    authorized = authorize_and_consume_payment_proof(
        engine, user=user, session_id=session_id, proof_token=proof,
        csrf_verified=csrf_verified, session_active=session_active, now=101,
    )
    if not authorized:
        return False
    provider.configure(destination)
    return True


@pytest.mark.parametrize("overrides", [
    {"user": LEARNER}, {"session_id": "wrong-session"},
    {"csrf_verified": False}, {"session_active": False},
    {"proof": "invalid-proof"},
])
def test_rejected_request_never_calls_fake_provider(tmp_path, overrides):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'provider.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        provider = FakeProvider()
        kwargs = dict(user=OWNER, session_id="s1", proof=proof,
                      csrf_verified=True, session_active=True,
                      destination="simulated-account")
        kwargs.update(overrides)
        assert not simulated_payment_request(engine, provider, **kwargs)
        assert provider.changes == []
        assert simulated_payment_request(
            engine, provider, user=OWNER, session_id="s1", proof=proof,
            csrf_verified=True, session_active=True, destination="simulated-account",
        )
        assert provider.changes == ["simulated-account"]
        assert not simulated_payment_request(
            engine, provider, user=OWNER, session_id="s1", proof=proof,
            csrf_verified=True, session_active=True, destination="simulated-account",
        )
        assert provider.changes == ["simulated-account"]
    finally:
        engine.dispose()
