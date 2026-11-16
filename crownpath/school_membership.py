"""Read-only school membership resolution for future device authorization.

This is not wired into HTTP routes or device discovery. Call only after
authenticating the principal from a verified server-side session.
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def verified_school_id(connection, principal):
    """Return the unique approved active school, otherwise None.

    Never trust a school identifier from client request parameters. Deny on
    ambiguous memberships, missing approval, revoked membership, or DB errors.
    """
    if not isinstance(principal, dict):
        return None
    user_id = principal.get("user_id")
    if (
        not isinstance(user_id, str) or not user_id
        or principal.get("active") is not True
    ):
        return None
    try:
        rows = connection.execute(text(
            "SELECT m.school_id FROM school_memberships AS m "
            "JOIN schools AS s ON s.school_id = m.school_id "
            "JOIN users AS u ON u.user_id = m.user_id "
            "WHERE m.user_id = :user_id "
            "AND u.active = TRUE AND s.active = TRUE "
            "AND m.active = TRUE AND m.revoked_at IS NULL "
            "AND m.approved_by_user_id IS NOT NULL "
            "AND m.approved_at IS NOT NULL"
        ), {"user_id": user_id}).fetchall()
    except SQLAlchemyError:
        return None
    return rows[0][0] if len(rows) == 1 and isinstance(rows[0][0], str) and rows[0][0] else None
