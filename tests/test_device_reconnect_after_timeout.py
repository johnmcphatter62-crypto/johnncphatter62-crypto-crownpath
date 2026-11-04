"""Synthetic CrownPath wireless reconnection authorization checks.

No Bluetooth, Wi-Fi, camera, or microphone hardware is accessed.
"""
import pytest


def can_reconnect(session, device):
    return (
        device["approved"]
        and not device["revoked"]
        and session["device_id"] == device["id"]
        and session["authorization_generation"] == device["authorization_generation"]
        and session["fresh_consent"]
    )


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_reconnect_with_new_authorization_and_consent(transport):
    device = {"id": "fictional-device", "transport": transport,
              "approved": True, "revoked": False,
              "authorization_generation": 2}
    session = {"device_id": "fictional-device",
               "authorization_generation": 2, "fresh_consent": True}
    assert can_reconnect(session, device)


def test_timed_out_old_authorization_cannot_reconnect():
    device = {"id": "fictional-device", "approved": True,
              "revoked": False, "authorization_generation": 2}
    session = {"device_id": "fictional-device",
               "authorization_generation": 1, "fresh_consent": True}
    assert not can_reconnect(session, device)


def test_fresh_authorization_without_consent_is_denied():
    device = {"id": "fictional-device", "approved": True,
              "revoked": False, "authorization_generation": 2}
    session = {"device_id": "fictional-device",
               "authorization_generation": 2, "fresh_consent": False}
    assert not can_reconnect(session, device)


def test_revoked_device_cannot_reconnect():
    device = {"id": "fictional-device", "approved": True,
              "revoked": True, "authorization_generation": 2}
    session = {"device_id": "fictional-device",
               "authorization_generation": 2, "fresh_consent": True}
    assert not can_reconnect(session, device)


def test_other_device_authorization_is_denied():
    device = {"id": "device-b", "approved": True,
              "revoked": False, "authorization_generation": 2}
    session = {"device_id": "device-a",
               "authorization_generation": 2, "fresh_consent": True}
    assert not can_reconnect(session, device)
