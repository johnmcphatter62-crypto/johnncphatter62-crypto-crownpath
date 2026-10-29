"""Fail-closed assignment activation/revocation helpers, not exposed as HTTP routes."""
from sqlalchemy.orm import Session

from crownpath.models import InstructorCourseAssignment, User


def set_course_assignment_active(
    db: Session, *, actor_user_id: str, assignment_id: str, active: bool
) -> InstructorCourseAssignment:
    """Only an active Owner can change a course assignment's status."""
    actor = db.get(User, actor_user_id)
    if actor is None or not actor.active or actor.role != "OWNER":
        raise PermissionError("Active Owner authorization required.")
    assignment = db.get(InstructorCourseAssignment, assignment_id)
    if assignment is None:
        raise ValueError("Assignment not found.")
    instructor = db.get(User, assignment.instructor_user_id)
    if active and (
        instructor is None or not instructor.active or instructor.role != "INSTRUCTOR"
    ):
        raise ValueError("Active instructor required to activate assignment.")
    assignment.active = bool(active)
    db.flush()
    return assignment


def instructor_can_edit_course(
    db: Session, *, instructor_user_id: str, course_id: str
) -> bool:
    """Fail closed unless the active instructor has an active course assignment."""
    from sqlalchemy import select

    instructor = db.get(User, instructor_user_id)
    if instructor is None or not instructor.active or instructor.role != "INSTRUCTOR":
        return False
    assignment = db.scalar(
        select(InstructorCourseAssignment).where(
            InstructorCourseAssignment.instructor_user_id == instructor_user_id,
            InstructorCourseAssignment.course_id == course_id,
            InstructorCourseAssignment.active.is_(True),
        )
    )
    return assignment is not None
