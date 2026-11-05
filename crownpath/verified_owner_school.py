"""Strict, read-only school scope resolution with verified Owner approval.

Staged for integration; not connected to HTTP or hardware. The caller must
authenticate the principal from a server-side session, not request input.
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def verified_owner_school_id(connection, principal):
    """Return exactly one active school approved by an active OWNER; else None."""
    if not isinstance(principal, dict):
        return None
    user_id = principal.get("user_id")
    if not isinstance(user_id, str) or not user_id or principal.get("active") is not True:
        return None
    try:
        rows = connection.execute(text(
            "SELECT m.school_id FROM school_memberships AS m "
            "JOIN schools AS s ON s.school_id = m.school_id "
            "JOIN users AS learner ON learner.user_id = m.user_id "
            "JOIN users AS approver ON approver.user_id = m.approved_by_user_id "
            "WHERE m.user_id = :user_id "
            "AND learner.active = TRUE AND s.active = TRUE "
            "AND m.active = TRUE AND m.revoked_at IS NULL "
            "AND m.approved_at IS NOT NULL "
            "AND approver.active = TRUE AND approver.role = 'OWNER'"
        ), {"user_id": user_id}).fetchall()
    except SQLAlchemyError:
        return None
    if len(rows) != 1:
        return None
    school_id = rows[0][0]
    return school_id if isinstance(school_id, str) and school_id else None
