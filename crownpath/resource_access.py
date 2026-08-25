import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from crownpath.audit import record_audit
from crownpath.database import session
from crownpath.models import ResourceAssignment
from crownpath.permissions import has_permission


def assign_resource(user_id, resource_type, resource_id, access_level="VIEW"):
    assignment = ResourceAssignment(
        assignment_id=f"CP-ASG-{uuid.uuid4().hex[:12].upper()}",
        user_id=user_id,
        resource_type=resource_type.upper(),
        resource_id=resource_id,
        access_level=access_level.upper(),
    )
    db = session()
    try:
        db.add(assignment)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    finally:
        db.close()


def has_assignment(user_id, resource_type, resource_id, access_level="VIEW"):
    requested = access_level.upper()
    db = session()
    try:
        row = db.scalar(
            select(ResourceAssignment).where(
                ResourceAssignment.user_id == user_id,
                ResourceAssignment.resource_type == resource_type.upper(),
                ResourceAssignment.resource_id == resource_id,
                ResourceAssignment.access_level.in_([requested, "MANAGE"]),
            )
        )
        return row is not None
    finally:
        db.close()


def can_access_resource(user, permission, resource_type, resource_id, access_level="VIEW"):
    if not has_permission(user, permission):
        record_audit(
            user["user_id"],
            "RESOURCE_ACCESS",
            "AUTHORIZATION",
            "DENIED",
            resource_type,
            resource_id,
            f"Missing permission: {permission}",
        )
        return False

    if user["role"].upper() == "OWNER":
        record_audit(
            user["user_id"],
            "RESOURCE_ACCESS",
            "AUTHORIZATION",
            "ALLOWED",
            resource_type,
            resource_id,
            "Owner access",
        )
        return True

    if resource_type.upper() == "LEARNER" and resource_id == user["user_id"]:
        record_audit(
            user["user_id"],
            "RESOURCE_ACCESS",
            "AUTHORIZATION",
            "ALLOWED",
            resource_type,
            resource_id,
            "Self access",
        )
        return True

    if has_assignment(user["user_id"], resource_type, resource_id, access_level):
        record_audit(
            user["user_id"],
            "RESOURCE_ACCESS",
            "AUTHORIZATION",
            "ALLOWED",
            resource_type,
            resource_id,
            "Assigned resource",
        )
        return True

    record_audit(
        user["user_id"],
        "RESOURCE_ACCESS",
        "AUTHORIZATION",
        "DENIED",
        resource_type,
        resource_id,
        "No object-level assignment",
    )
    return False
