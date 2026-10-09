"""Authorization policy for proposed CrownPath instructor reviews.

Pure policy only: caller must establish that the assignment is active and
belongs to the learner, verify evidence, and audit persisted decisions.
"""
from crownpath.permissions import has_permission


def can_review_learner(instructor: dict | None, learner_id: str, assigned_learner_ids: set[str]) -> bool:
    if not instructor or not instructor.get("user_id") or not learner_id:
        return False
    if instructor["user_id"] == learner_id:
        return False
    if instructor.get("role", "").upper() == "OWNER":
        return has_permission(instructor, "academy.manage")
    return (
        instructor.get("role", "").upper() == "INSTRUCTOR"
        and has_permission(instructor, "academy.manage_assigned")
        and learner_id in assigned_learner_ids
    )


def can_review_assigned_learner(instructor: dict | None, learner_id: str) -> bool:
    """Authorize review using server-side CrownPath resource assignments.

    No API endpoint or assessment write is performed here. Existing assignments
    use resource_type=LEARNER and access_level=MANAGE for instructor reviews.
    """
    if not instructor or not learner_id or not instructor.get("user_id"):
        return False
    if instructor["user_id"] == learner_id:
        return False
    role = instructor.get("role", "").upper()
    if role == "OWNER":
        return has_permission(instructor, "academy.manage")
    if role != "INSTRUCTOR" or not has_permission(instructor, "academy.manage_assigned"):
        return False
    from crownpath.resource_access import has_assignment
    return has_assignment(instructor["user_id"], "LEARNER", learner_id, "MANAGE")
