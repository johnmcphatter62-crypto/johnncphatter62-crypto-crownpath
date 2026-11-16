"""Read-only approval integrity check for school membership.

Not wired into HTTP routes or device discovery. Intended as a prerequisite
for replacing the current membership resolver after integration tests.
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def owner_approved_membership(connection, membership_id):
    """Require an active OWNER who approved an active, unrevoked membership.

    A populated approver identifier alone is insufficient proof of approval.
    """
    if not isinstance(membership_id, str) or not membership_id:
        return False
    try:
        matches = connection.execute(text(
            "SELECT m.membership_id FROM school_memberships AS m "
            "JOIN users AS learner ON learner.user_id = m.user_id "
            "JOIN schools AS s ON s.school_id = m.school_id "
            "JOIN users AS approver ON approver.user_id = m.approved_by_user_id "
            "WHERE m.membership_id = :membership_id "
            "AND learner.active = TRUE AND s.active = TRUE "
            "AND m.active = TRUE AND m.revoked_at IS NULL "
            "AND m.approved_at IS NOT NULL "
            "AND approver.active = TRUE AND approver.role = 'OWNER'"
        ), {"membership_id": membership_id}).fetchall()
    except SQLAlchemyError:
        return False
    return len(matches) == 1
