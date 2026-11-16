"""Staged device visibility must not mutate input records or containers."""
from copy import deepcopy

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "device-a", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


def test_visibility_does_not_mutate_original_records():
    principal = deepcopy(PRINCIPAL)
    devices = [deepcopy(DEVICE), dict(DEVICE, id="device-b", approved=False)]
    original_principal = deepcopy(principal)
    original_devices = deepcopy(devices)

    result = visible_approved_devices(principal, devices)

    assert principal == original_principal
    assert devices == original_devices
    assert result == [DEVICE]
    assert result[0] is not devices[0]


def test_modifying_returned_record_does_not_modify_source_record():
    devices = [deepcopy(DEVICE)]
    result = visible_approved_devices(PRINCIPAL, devices)

    result[0]["approved"] = False
    result[0]["id"] = "modified"

    assert devices == [DEVICE]
    assert [record["id"] for record in visible_approved_devices(
        PRINCIPAL, devices
    )] == ["device-a"]


def test_duplicate_filter_does_not_mutate_or_remove_source_records():
    devices = [deepcopy(DEVICE), dict(DEVICE, approved=False),
               dict(DEVICE, id="device-b")]
    original = deepcopy(devices)

    result = visible_approved_devices(PRINCIPAL, devices)

    assert [record["id"] for record in result] == ["device-b"]
    assert devices == original
    assert len(devices) == 3
