"""Staged read-only school resolver requiring same-school Owner authority.

Not connected to HTTP routes or hardware. The principal must be derived from
a trusted server-side session. No school ID is accepted from the client.
"""
from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from crownpath.school_owner_authority import owner_authorized_for_school


def scoped_owner_school_id(connection, principal, *, now=None):
    """Return a learner's single active school only if its approver is authorized."""
    if not isinstance(principal, Mapping):
        return None
    user_id = principal.get("user_id")
    if not isinstance(user_id, str) or not user_id or principal.get("active") is not True:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        return None
    try:
        rows = connection.execute(text(
            "SELECT m.school_id, m.approved_by_user_id, m.approved_at "
            "FROM school_memberships AS m "
            "JOIN schools AS s ON s.school_id = m.school_id "
            "JOIN users AS learner ON learner.user_id = m.user_id "
            "WHERE m.user_id = :user_id "
            "AND learner.active = TRUE AND s.active = TRUE "
            "AND m.active = TRUE AND m.revoked_at IS NULL "
            "AND m.approved_at IS NOT NULL "
            "AND m.approved_at <= :now"
        ), {"user_id": user_id, "now": now}).fetchall()
    except (SQLAlchemyError, TypeError, ValueError):
        return None
    if len(rows) != 1:
        return None
    school_id, approver_id, approved_at = rows[0]
    if not isinstance(school_id, str) or not school_id:
        return None
    if not owner_authorized_for_school(connection, approver_id, school_id, now=now):
        return None
    # A grant issued after membership approval cannot retroactively authorize it.
    try:
        grants = connection.execute(text(
            "SELECT authorization_id FROM school_owner_authorizations "
            "WHERE owner_user_id = :owner_id AND school_id = :school_id "
            "AND active = TRUE AND revoked_at IS NULL "
            "AND granted_at <= :approved_at "
            "AND (expires_at IS NULL OR expires_at > :now)"
        ), {"owner_id": approver_id, "school_id": school_id,
            "approved_at": approved_at, "now": now}).fetchall()
    except (SQLAlchemyError, TypeError, ValueError):
        return None
    if len(grants) != 1:
        return None
    return school_id
