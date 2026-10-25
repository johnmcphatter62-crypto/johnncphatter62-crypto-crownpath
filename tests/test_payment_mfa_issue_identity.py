"""Malformed identities and session values must fail closed before proof issuance."""
import pytest
from crownpath.payment_mfa_issue_policy import may_issue_payment_proof

BASE = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("user", [
    None, {}, {"role": "OWNER", "active": True, "mfa_enabled": True},
    {"user_id": "", "role": "OWNER", "active": True, "mfa_enabled": True},
    {"user_id": None, "role": "OWNER", "active": True, "mfa_enabled": True},
])
def test_missing_owner_identity_denied(user):
    assert not may_issue_payment_proof(
        user, server_verified_mfa=True, session_id="session",
        csrf_verified=True,
    )

@pytest.mark.parametrize("session_id", [None, "", "   ", 42, True, []])
def test_malformed_session_id_denied(session_id):
    assert not may_issue_payment_proof(
        BASE, server_verified_mfa=True, session_id=session_id,
        csrf_verified=True,
    )

def test_valid_server_derived_inputs_accepted():
    assert may_issue_payment_proof(
        BASE, server_verified_mfa=True, session_id="session",
        csrf_verified=True,
    )
