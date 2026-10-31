"""Isolated security regression tests for payment configuration permissions.

These tests define a deny-by-default role-permission contract.
They do not verify endpoint authorization or MFA enforcement.
No payment provider, credentials, or production database is contacted.
"""
import pytest
from crownpath.permissions import has_permission

@pytest.mark.parametrize("role", ["INSTRUCTOR", "BARBER", "COSMETOLOGY_PRO", "HOME_CARE", "UNKNOWN"])
def test_non_owner_cannot_manage_payment_configuration(role):
    assert not has_permission({"active": True, "role": role}, "payments.configure")

def test_inactive_owner_cannot_manage_payment_configuration():
    assert not has_permission({"active": False, "role": "OWNER"}, "payments.configure")

def test_active_owner_has_payment_configuration_permission():
    assert has_permission({"active": True, "role": "OWNER"}, "payments.configure")
