"""Fail-closed regression checks for malformed staged device containers."""
import pytest

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "approved", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("devices", [
    None,
    True,
    12,
    3.14,
    "device-id",
    b"device-id",
    bytearray(b"device-id"),
    {"id": "approved"},
    (device for device in [DEVICE]),
])
def test_malformed_container_denied_without_exception(devices):
    assert visible_approved_devices(PRINCIPAL, devices) == []


def test_sequence_filters_malformed_records_but_keeps_authorized_device():
    records = [None, 42, "invalid", {}, DEVICE,
               dict(DEVICE, id="unapproved", approved=False),
               dict(DEVICE, id="foreign", school_id="another-school")]
    assert [d["id"] for d in visible_approved_devices(PRINCIPAL, records)] == ["approved"]


def test_tuple_of_trusted_records_supported():
    assert visible_approved_devices(PRINCIPAL, (DEVICE,)) == [DEVICE]
