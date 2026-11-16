"""Read-only device access composition; not exposed as an HTTP endpoint.

Call only with a server-authenticated principal and trusted device records.
No hardware discovery, permissions, or connection attempts occur here.
"""
from collections.abc import Mapping

from crownpath.device_visibility import visible_approved_devices
from crownpath.school_membership import verified_school_id


def authorized_visible_devices(connection, principal, device_records):
    """Filter devices using DB-verified school membership, never client scope."""
    if not isinstance(principal, Mapping):
        return []
    user_id = principal.get("user_id")
    if not isinstance(user_id, str) or not user_id or principal.get("active") is not True:
        return []
    school_id = verified_school_id(connection, {
        "user_id": user_id,
        "active": principal["active"],
    })
    if school_id is None:
        return []
    # Only the database resolver can supply the school scope.
    verified_principal = {"user_id": user_id, "school_id": school_id, "active": True}
    return visible_approved_devices(verified_principal, device_records)
