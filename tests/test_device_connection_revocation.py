"""Synthetic CrownPath device permission revocation tests.

These checks do not interact with Bluetooth or Wi-Fi hardware.
"""
import pytest


def can_connect(device, now):
    if device["revoked"]:
        return False
    if not device["approved"]:
        return False
    if device["expires_at"] <= now:
        return False
    return True


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_approved_device_connects_before_expiry(transport):
    device = {"transport": transport, "approved": True,
              "revoked": False, "expires_at": 200}
    assert can_connect(device, 100)


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_revoked_device_cannot_reconnect(transport):
    device = {"transport": transport, "approved": True,
              "revoked": True, "expires_at": 200}
    assert not can_connect(device, 100)


def test_permission_expiry_blocks_connection():
    device = {"transport": "wifi", "approved": True,
              "revoked": False, "expires_at": 100}
    assert not can_connect(device, 100)


def test_unapproved_device_cannot_connect():
    device = {"transport": "bluetooth", "approved": False,
              "revoked": False, "expires_at": 200}
    assert not can_connect(device, 100)
