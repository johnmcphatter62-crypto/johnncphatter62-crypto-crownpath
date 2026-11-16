"""Test-only signed session adapter; not connected to any HTTP or payment route.

JWT verification alone is insufficient. Caller must provide a trusted database
session check and user status check; both must succeed.
"""
import jwt


def validate_signed_session(token, *, secret, algorithm, active_session, active_user):
    if not isinstance(token, str) or not token.strip():
        return None
    try:
        claims = jwt.decode(token, secret, algorithms=[algorithm])
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return None
    if claims.get("purpose") != "session":
        return None
    user_id, session_id = claims.get("sub"), claims.get("jti")
    if not isinstance(user_id, str) or not user_id.strip():
        return None
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    try:
        if active_session(user_id, session_id) is not True:
            return None
        if active_user(user_id) is not True:
            return None
    except Exception:
        return None
    return {"user_id": user_id, "session_id": session_id}
