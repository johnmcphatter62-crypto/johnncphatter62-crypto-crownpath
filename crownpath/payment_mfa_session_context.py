"""Test-only, fail-closed session context extraction.

This does not authorize payment changes or replace the application's
authoritative JWT/database session validation.
"""
from collections.abc import Callable


def verified_session_context(token, *, decode_and_check: Callable):
    """Return validated (user_id, session_id) or None.

    decode_and_check must verify JWT signature, expiry, purpose, active DB
    session, user status and role *before* returning claims. Never supply
    unverified JWT claims or request JSON as the callback result.
    """
    if not isinstance(token, str) or not token.strip():
        return None
    try:
        claims = decode_and_check(token)
    except Exception:
        return None
    if not isinstance(claims, dict):
        return None
    user_id = claims.get("user_id")
    session_id = claims.get("session_id")
    if not isinstance(user_id, str) or not user_id.strip():
        return None
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    return user_id, session_id
