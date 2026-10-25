"""Fail-closed policy boundary for experimental payment MFA proof issuance.

This pure function performs no MFA verification, database access, or routing.
It must only be called with server-derived, independently verified inputs.
"""
from crownpath.payment_access import can_configure_payments


def may_issue_payment_proof(
    user, *, server_verified_mfa=False, session_id=None, csrf_verified=False
):
    """Deny unless owner permission, server MFA, session, and CSRF all pass."""
    return bool(
        isinstance(user, dict)
        and isinstance(user.get("user_id"), str)
        and bool(user["user_id"].strip())
        and isinstance(session_id, str)
        and bool(session_id.strip())
        and csrf_verified is True
        and server_verified_mfa is True
        and can_configure_payments(user, recent_mfa_verified=True)
    )
