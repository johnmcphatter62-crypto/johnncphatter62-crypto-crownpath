"""Pure policy tests; no live MFA codes, sessions, or payment providers."""
import pytest
from crownpath.payment_mfa_issue_policy import may_issue_payment_proof

OWNER = {"role": "OWNER", "active": True, "mfa_enabled": True}

def test_all_trusted_conditions_required():
    assert may_issue_payment_proof(OWNER, server_verified_mfa=True, session_id="trusted-session", csrf_verified=True)

@pytest.mark.parametrize("overrides", [
    {"server_verified_mfa": False},
    {"server_verified_mfa": "true"},
    {"session_id": ""},
    {"session_id": None},
    {"csrf_verified": False},
    {"csrf_verified": "true"},
])
def test_untrusted_or_missing_conditions_denied(overrides):
    conditions = {"server_verified_mfa": True, "session_id": "trusted-session", "csrf_verified": True}
    conditions.update(overrides)
    assert not may_issue_payment_proof(OWNER, **conditions)

@pytest.mark.parametrize("user", [
    None,
    {"role": "STUDENT", "active": True, "mfa_enabled": True},
    {"role": "OWNER", "active": False, "mfa_enabled": True},
    {"role": "OWNER", "active": True, "mfa_enabled": False},
])
def test_non_owner_or_inactive_or_mfa_disabled_denied(user):
    assert not may_issue_payment_proof(user, server_verified_mfa=True, session_id="trusted-session", csrf_verified=True)
