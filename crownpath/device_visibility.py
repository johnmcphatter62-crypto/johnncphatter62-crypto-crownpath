"""Fail-closed device-list visibility policy for future CrownPath integration.

This module does not scan hardware, query the database, or expose an API.
Callers must derive the principal from a verified server-side session.
"""
from collections.abc import Mapping

SUPPORTED_TRANSPORTS = frozenset({"bluetooth", "wifi"})


def visible_approved_devices(principal, devices):
    """Return allowed device records for an authenticated active learner.

    Reject incomplete identities and malformed device records. The caller is
    responsible for authenticating the principal and supplying trusted records.
    """
    if not isinstance(principal, Mapping):
        return []
    user_id = principal.get("user_id")
    school_id = principal.get("school_id")
    if (
        not isinstance(user_id, str)
        or not user_id
        or not isinstance(school_id, str)
        or not school_id
        or principal.get("active") is not True
    ):
        return []

    allowed = []
    for device in devices:
        if not isinstance(device, Mapping):
            continue
        if (
            device.get("owner_id") == user_id
            and device.get("school_id") == school_id
            and device.get("approved") is True
            and device.get("revoked") is False
            and device.get("transport") in SUPPORTED_TRANSPORTS
            and isinstance(device.get("id"), str)
            and bool(device["id"])
        ):
            allowed.append(dict(device))
    return allowed
