"""Unhashable or unsupported transport values must not crash device filtering."""
import pytest

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "valid", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("bad_transport", [
    ["wifi"], {"kind": "wifi"}, set(["wifi"]), None, 123, True, "",
])
def test_malformed_transport_is_excluded_without_exception(bad_transport):
    malformed = dict(DEVICE, id="malformed", transport=bad_transport)
    result = visible_approved_devices(PRINCIPAL, [malformed, DEVICE])
    assert [device["id"] for device in result] == ["valid"]


def test_only_exact_supported_transport_strings_are_allowed():
    devices = [
        dict(DEVICE, id="wifi", transport="wifi"),
        dict(DEVICE, id="bluetooth", transport="bluetooth"),
        dict(DEVICE, id="uppercase", transport="WIFI"),
        dict(DEVICE, id="padded", transport=" wifi "),
    ]
    assert [device["id"] for device in visible_approved_devices(
        PRINCIPAL, devices
    )] == ["wifi", "bluetooth"]
