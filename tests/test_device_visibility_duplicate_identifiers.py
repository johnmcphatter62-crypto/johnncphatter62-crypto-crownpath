"""Staged device records with duplicate identifiers must fail closed."""
import pytest

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
BASE = {"id": "device-a", "owner_id": "learner", "school_id": "school-a",
        "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("duplicate", [
    dict(BASE),
    dict(BASE, revoked=True),
    dict(BASE, approved=False),
    dict(BASE, owner_id="other-learner"),
    dict(BASE, school_id="other-school"),
    {"id": "device-a"},
])
def test_duplicate_id_hides_all_ambiguous_records(duplicate):
    unrelated = dict(BASE, id="device-b")
    result = visible_approved_devices(PRINCIPAL, [BASE, duplicate, unrelated])
    assert [device["id"] for device in result] == ["device-b"]


def test_unique_ids_remain_visible_and_ordered():
    second = dict(BASE, id="device-b", transport="bluetooth")
    assert [d["id"] for d in visible_approved_devices(
        PRINCIPAL, [BASE, second]
    )] == ["device-a", "device-b"]


def test_non_string_ids_do_not_hide_valid_record():
    assert visible_approved_devices(
        PRINCIPAL, [BASE, dict(BASE, id=123)]
    ) == [BASE]
