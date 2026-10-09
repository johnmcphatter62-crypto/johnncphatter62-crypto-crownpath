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
