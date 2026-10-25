"""Payment API security contract; no real payment provider or secrets.

This contract documents requirements for future payment administration endpoints.
It is intentionally not a payment-processing implementation.
"""
from crownpath.permissions import has_permission

PAYMENT_ADMIN_PERMISSION = "payments.configure"

def can_configure_payments(user: dict | None) -> bool:
    """Deny access unless active OWNER with MFA enabled."""
    return bool(
        user
        and user.get("role") == "OWNER"
        and user.get("active") is True
        and user.get("mfa_enabled") is True
        and has_permission(user, PAYMENT_ADMIN_PERMISSION)
    )
