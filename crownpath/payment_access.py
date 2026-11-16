"""Fail-closed authorization for future payment administration.

This helper does not process payments, validate MFA codes, or authorize a real API.
Callers must independently validate a fresh, purpose-bound MFA confirmation.
"""
from crownpath.permissions import has_permission

PAYMENT_ADMIN_PERMISSION = "payments.configure"

def can_configure_payments(user: dict | None, *, recent_mfa_verified: bool = False) -> bool:
    """Require active owner, enabled MFA, and a fresh verified MFA assertion."""
    return bool(
        user
        and user.get("role") == "OWNER"
        and user.get("active") is True
        and user.get("mfa_enabled") is True
        and recent_mfa_verified is True
        and has_permission(user, PAYMENT_ADMIN_PERMISSION)
    )
