"""Synthetic CrownPath approved-device discovery visibility tests.

No hardware scanning or wireless pairing occurs.
"""
import pytest


def visible_devices(user, devices):
    if not user or not user.get("active"):
        return []
    return [
        device["id"]
        for device in devices
        if device["school_id"] == user["school_id"]
        and device["owner_id"] == user["id"]
        and device["approved"]
        and not device["revoked"]
        and device["transport"] in {"bluetooth", "wifi"}
    ]


@pytest.fixture
def devices():
    return [
        {"id": "own-bluetooth", "school_id": "school-a",
         "owner_id": "learner-a", "approved": True,
         "revoked": False, "transport": "bluetooth"},
        {"id": "own-wifi", "school_id": "school-a",
         "owner_id": "learner-a", "approved": True,
         "revoked": False, "transport": "wifi"},
        {"id": "other-learner", "school_id": "school-a",
         "owner_id": "learner-b", "approved": True,
         "revoked": False, "transport": "bluetooth"},
        {"id": "other-school", "school_id": "school-b",
         "owner_id": "learner-a", "approved": True,
         "revoked": False, "transport": "wifi"},
        {"id": "unapproved", "school_id": "school-a",
         "owner_id": "learner-a", "approved": False,
         "revoked": False, "transport": "bluetooth"},
        {"id": "revoked", "school_id": "school-a",
         "owner_id": "learner-a", "approved": True,
         "revoked": True, "transport": "wifi"},
        {"id": "unsupported", "school_id": "school-a",
         "owner_id": "learner-a", "approved": True,
         "revoked": False, "transport": "unknown"},
    ]


def test_only_own_approved_devices_are_visible(devices):
    user = {"id": "learner-a", "school_id": "school-a", "active": True}
    assert visible_devices(user, devices) == ["own-bluetooth", "own-wifi"]


def test_other_learner_cannot_see_devices(devices):
    user = {"id": "learner-c", "school_id": "school-a", "active": True}
    assert visible_devices(user, devices) == []


def test_other_school_cannot_see_devices(devices):
    user = {"id": "learner-a", "school_id": "school-c", "active": True}
    assert visible_devices(user, devices) == []


def test_inactive_user_sees_no_devices(devices):
    user = {"id": "learner-a", "school_id": "school-a", "active": False}
    assert visible_devices(user, devices) == []


def test_unauthenticated_user_sees_no_devices(devices):
    assert visible_devices(None, devices) == []
