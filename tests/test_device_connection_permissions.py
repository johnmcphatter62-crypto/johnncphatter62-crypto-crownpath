"""Synthetic CrownPath device authorization checks.

No hardware discovery, Bluetooth pairing, or network connections occur.
"""
import pytest


def may_connect(user, device):
    if not user or not user.get("active"):
        return False
    if device.get("transport") not in {"bluetooth", "wifi"}:
        return False
    if user.get("school_id") != device.get("school_id"):
        return False
    if device.get("owner_id") != user.get("id"):
        return False
    return bool(device.get("approved"))


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_owner_can_use_approved_device(transport):
    user = {"id": "learner-a", "school_id": "school-a", "active": True}
    device = {"owner_id": "learner-a", "school_id": "school-a",
              "transport": transport, "approved": True}
    assert may_connect(user, device)


def test_other_student_device_is_denied():
    user = {"id": "learner-b", "school_id": "school-a", "active": True}
    device = {"owner_id": "learner-a", "school_id": "school-a",
              "transport": "bluetooth", "approved": True}
    assert not may_connect(user, device)


def test_other_school_device_is_denied():
    user = {"id": "learner-a", "school_id": "school-b", "active": True}
    device = {"owner_id": "learner-a", "school_id": "school-a",
              "transport": "wifi", "approved": True}
    assert not may_connect(user, device)


def test_unapproved_device_is_denied():
    user = {"id": "learner-a", "school_id": "school-a", "active": True}
    device = {"owner_id": "learner-a", "school_id": "school-a",
              "transport": "bluetooth", "approved": False}
    assert not may_connect(user, device)


def test_inactive_user_is_denied():
    user = {"id": "learner-a", "school_id": "school-a", "active": False}
    device = {"owner_id": "learner-a", "school_id": "school-a",
              "transport": "wifi", "approved": True}
    assert not may_connect(user, device)


def test_unknown_transport_is_denied():
    user = {"id": "learner-a", "school_id": "school-a", "active": True}
    device = {"owner_id": "learner-a", "school_id": "school-a",
              "transport": "unknown", "approved": True}
    assert not may_connect(user, device)
