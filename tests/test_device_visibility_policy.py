"""Tests for the actual CrownPath device-visibility policy.

Uses synthetic identities and records only; no device hardware or HTTP API.
"""
import pytest

from crownpath.device_visibility import visible_approved_devices


@pytest.fixture
def principal():
    return {"user_id": "learner-1", "school_id": "school-1", "active": True}


@pytest.fixture
def approved_device():
    return {
        "id": "device-1", "owner_id": "learner-1", "school_id": "school-1",
        "approved": True, "revoked": False, "transport": "bluetooth",
    }


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_own_approved_device_visible(principal, approved_device, transport):
    approved_device["transport"] = transport
    assert visible_approved_devices(principal, [approved_device]) == [approved_device]


@pytest.mark.parametrize("change", [
    {"owner_id": "learner-2"},
    {"school_id": "school-2"},
    {"approved": False},
    {"revoked": True},
    {"transport": "unknown"},
    {"id": ""},
    {"approved": "true"},
    {"revoked": 0},
])
def test_untrusted_or_unauthorized_records_hidden(principal, approved_device, change):
    approved_device.update(change)
    assert visible_approved_devices(principal, [approved_device]) == []


@pytest.mark.parametrize("identity", [
    None, {}, {"user_id": "learner-1", "active": True},
    {"user_id": "learner-1", "school_id": "school-1", "active": False},
    {"user_id": "", "school_id": "school-1", "active": True},
    {"user_id": "learner-1", "school_id": "", "active": True},
    {"user_id": "learner-1", "school_id": "school-1", "active": 1},
])
def test_missing_or_inactive_principal_denied(identity, approved_device):
    assert visible_approved_devices(identity, [approved_device]) == []


def test_malformed_records_ignored(principal, approved_device):
    assert visible_approved_devices(principal, [None, {}, "bad", approved_device]) == [
        approved_device
    ]


def test_result_is_not_original_mutable_record(principal, approved_device):
    visible = visible_approved_devices(principal, [approved_device])
    visible[0]["id"] = "modified"
    assert approved_device["id"] == "device-1"
