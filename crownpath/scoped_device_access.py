"""Staged device visibility requiring an Owner grant for the same school.

Not connected to application routes or real Bluetooth/Wi-Fi hardware.
Callers must supply a trusted server-authenticated principal and trusted records.
"""
from collections.abc import Mapping
from datetime import datetime, timezone

from crownpath.device_visibility import visible_approved_devices
from crownpath.scoped_owner_school import scoped_owner_school_id


def scoped_authorized_visible_devices(connection, principal, device_records, *, now=None):
    """Deny device visibility unless membership and same-school Owner grant pass."""
    if not isinstance(principal, Mapping):
        return []
    user_id = principal.get("user_id")
    if not isinstance(user_id, str) or not user_id or principal.get("active") is not True:
        return []
    if now is None:
        now = datetime.now(timezone.utc)
    school_id = scoped_owner_school_id(
        connection, {"user_id": user_id, "active": True}, now=now
    )
    if school_id is None:
        return []
    return visible_approved_devices(
        {"user_id": user_id, "school_id": school_id, "active": True},
        device_records,
    )
