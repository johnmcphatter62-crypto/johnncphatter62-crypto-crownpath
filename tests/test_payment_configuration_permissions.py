"""Isolated security regression tests for payment configuration permissions.

These tests define a deny-by-default contract. They intentionally fail until
server-side payment authorization is implemented and verified.
No payment provider, credentials, or production database is contacted.
"""
import pytest
from crownpath.permissions import has_permission

@pytest.mark.parametrize("role", ["INSTRUCTOR", "BARBER", "COSMETOLOGY_PRO", "HOME_CARE", "UNKNOWN"])
def test_non_owner_cannot_manage_payment_configuration(role):
    assert not has_permission({"active": True, "role": role}, "payments.configure")

def test_inactive_owner_cannot_manage_payment_configuration():
    assert not has_permission({"active": False, "role": "OWNER"}, "payments.configure")

@pytest.mark.xfail(strict=True, reason="Payment configuration permission and MFA enforcement not yet implemented")
def test_active_owner_payment_configuration_requires_server_side_authorization():
    assert has_permission({"active": True, "role": "OWNER"}, "payments.configure")
