"""Fail-closed, route-independent guard for consuming payment MFA proofs.

Callers must derive user and session from a validated server-side session,
verify CSRF independently, and confirm the session is not revoked. This is
NOT an HTTP endpoint or production payment configuration integration.
"""
from crownpath.payment_access import can_configure_payments
from crownpath.payment_mfa_db_proof import consume_proof


def authorize_and_consume_payment_proof(
    engine, *, user, session_id, proof_token, csrf_verified=False,
    session_active=False, now=None,
):
    """Consume only when all trusted preconditions are explicitly true."""
    if not (
        isinstance(user, dict)
        and isinstance(user.get("user_id"), str)
        and bool(user["user_id"].strip())
        and can_configure_payments(user, recent_mfa_verified=True)
        and isinstance(session_id, str)
        and bool(session_id.strip())
        and isinstance(proof_token, str)
        and bool(proof_token)
        and csrf_verified is True
        and session_active is True
    ):
        return False
    return consume_proof(
        engine, token=proof_token, user_id=user["user_id"],
        session_id=session_id, now=now,
    )
