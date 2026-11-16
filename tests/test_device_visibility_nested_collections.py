"""Nested device collections must not be interpreted as trusted device records."""
from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "valid", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


def test_nested_list_of_devices_is_not_automatically_flattened():
    assert visible_approved_devices(PRINCIPAL, [[DEVICE]]) == []


def test_nested_mapping_wrapper_is_not_treated_as_device():
    assert visible_approved_devices(PRINCIPAL, [{"devices": [DEVICE]}]) == []


def test_mixed_nested_collections_do_not_hide_unique_valid_device():
    records = [[dict(DEVICE, id="nested")], {"devices": [DEVICE]},
               None, (), dict(DEVICE, id="valid")]
    result = visible_approved_devices(PRINCIPAL, records)
    assert [record["id"] for record in result] == ["valid"]


def test_tuple_container_with_malformed_nested_items_remains_fail_closed():
    records = ({"devices": [DEVICE]}, (DEVICE,), dict(DEVICE))
    result = visible_approved_devices(PRINCIPAL, records)
    assert [record["id"] for record in result] == ["valid"]
