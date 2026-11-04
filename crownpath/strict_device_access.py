"""Staged strict device visibility, not wired to routes or live hardware.

Only a server-authenticated principal and trusted device records may be used.
The database must verify that an active OWNER approved the school membership.
"""
from collections.abc import Mapping

from crownpath.device_visibility import visible_approved_devices
from crownpath.verified_owner_school import verified_owner_school_id


def strict_authorized_visible_devices(connection, principal, device_records):
    """Return only devices belonging to the DB-verified Owner-approved school."""
    if not isinstance(principal, Mapping):
        return []
    user_id = principal.get("user_id")
    if not isinstance(user_id, str) or not user_id or principal.get("active") is not True:
        return []
    school_id = verified_owner_school_id(
        connection, {"user_id": user_id, "active": True}
    )
    if school_id is None:
        return []
    return visible_approved_devices(
        {"user_id": user_id, "school_id": school_id, "active": True},
        device_records,
    )
