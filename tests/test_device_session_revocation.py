"""Synthetic CrownPath device session authorization checks.

No Bluetooth, Wi-Fi, or production sessions are opened.
"""
import pytest


def session_allowed(session, device):
    return (
        session["device_id"] == device["id"]
        and session["permission_version"] == device["permission_version"]
        and device["approved"]
        and not device["revoked"]
    )


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_current_approved_session_is_allowed(transport):
    device = {"id": "fictional-device", "transport": transport,
              "permission_version": 3, "approved": True, "revoked": False}
    session = {"device_id": "fictional-device", "permission_version": 3}
    assert session_allowed(session, device)


def test_revoked_device_session_is_denied():
    device = {"id": "fictional-device", "permission_version": 4,
              "approved": True, "revoked": True}
    session = {"device_id": "fictional-device", "permission_version": 3}
    assert not session_allowed(session, device)


def test_old_session_cannot_survive_permission_version_change():
    device = {"id": "fictional-device", "permission_version": 4,
              "approved": True, "revoked": False}
    session = {"device_id": "fictional-device", "permission_version": 3}
    assert not session_allowed(session, device)


def test_session_for_different_device_is_denied():
    device = {"id": "fictional-device-b", "permission_version": 3,
              "approved": True, "revoked": False}
    session = {"device_id": "fictional-device-a", "permission_version": 3}
    assert not session_allowed(session, device)


def test_unapproved_device_session_is_denied():
    device = {"id": "fictional-device", "permission_version": 3,
              "approved": False, "revoked": False}
    session = {"device_id": "fictional-device", "permission_version": 3}
    assert not session_allowed(session, device)
