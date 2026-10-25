"""Synthetic payment admin authorization checks. No provider or DB calls."""
import pytest
from crownpath.payment_access import can_configure_payments

@pytest.mark.parametrize("role", ["INSTRUCTOR", "BARBER", "COSMETOLOGY_PRO", "HOME_CARE", "UNKNOWN"])
def test_non_owner_denied_even_with_fresh_mfa(role):
    assert not can_configure_payments({"role":role,"active":True,"mfa_enabled":True},recent_mfa_verified=True)

def test_owner_denied_without_mfa():
    assert not can_configure_payments({"role":"OWNER","active":True,"mfa_enabled":False},recent_mfa_verified=True)

def test_inactive_owner_denied():
    assert not can_configure_payments({"role":"OWNER","active":False,"mfa_enabled":True},recent_mfa_verified=True)

def test_owner_denied_without_recent_mfa_assertion():
    assert not can_configure_payments({"role":"OWNER","active":True,"mfa_enabled":True})

def test_owner_with_recent_mfa_assertion_allowed_at_helper_level():
    assert can_configure_payments({"role":"OWNER","active":True,"mfa_enabled":True},recent_mfa_verified=True)
