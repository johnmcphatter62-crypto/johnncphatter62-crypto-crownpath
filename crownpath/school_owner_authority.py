"""Staged school-scoped Owner authority check.

Read-only policy. No grants, routes, live devices, or production integration.
"""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def owner_authorized_for_school(connection, owner_user_id, school_id, *, now=None):
    """Verify one active, unrevoked, unexpired Owner grant for this school.

    The owner and school identifiers must come from trusted server-side records.
    """
    if (
        not isinstance(owner_user_id, str)
        or not owner_user_id
        or not isinstance(school_id, str)
        or not school_id
    ):
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        return False
    try:
        rows = connection.execute(text(
            "SELECT a.authorization_id FROM school_owner_authorizations AS a "
            "JOIN users AS u ON u.user_id = a.owner_user_id "
            "JOIN schools AS s ON s.school_id = a.school_id "
            "WHERE a.owner_user_id = :owner_user_id AND a.school_id = :school_id "
            "AND a.active = TRUE AND a.revoked_at IS NULL "
            "AND a.granted_at <= :now "
            "AND (a.expires_at IS NULL OR a.expires_at > :now) "
            "AND u.active = TRUE AND u.role = 'OWNER' AND s.active = TRUE"
        ), {
            "owner_user_id": owner_user_id,
            "school_id": school_id,
            "now": now,
        }).fetchall()
    except (SQLAlchemyError, TypeError, ValueError):
        return False
    return len(rows) == 1
