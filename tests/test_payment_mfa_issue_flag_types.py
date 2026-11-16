"""Pure payment MFA issuance policy must reject non-boolean trust assertions."""
import pytest
from crownpath.payment_mfa_issue_policy import may_issue_payment_proof

OWNER = {"user_id": "owner", "role": "OWNER", "active": True, "mfa_enabled": True}

@pytest.mark.parametrize("field,value", [
    ("server_verified_mfa", None), ("server_verified_mfa", 1),
    ("server_verified_mfa", "true"), ("server_verified_mfa", []),
    ("csrf_verified", None), ("csrf_verified", 1),
    ("csrf_verified", "true"), ("csrf_verified", []),
])
def test_non_boolean_issuance_flags_denied(field, value):
    kwargs = dict(server_verified_mfa=True, session_id="s1", csrf_verified=True)
    kwargs[field] = value
    assert not may_issue_payment_proof(OWNER, **kwargs)
    kwargs[field] = True
    assert may_issue_payment_proof(OWNER, **kwargs)
