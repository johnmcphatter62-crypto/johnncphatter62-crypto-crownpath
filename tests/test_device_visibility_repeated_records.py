"""Repeated device records must be treated as ambiguous in any order."""
from itertools import permutations

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
BASE = {"id": "repeated", "owner_id": "learner", "school_id": "school-a",
        "approved": True, "revoked": False, "transport": "wifi"}


def test_repeated_identical_records_are_denied():
    assert visible_approved_devices(PRINCIPAL, [dict(BASE), dict(BASE)]) == []


def test_repeated_identifier_is_denied_in_any_record_order():
    repeated = dict(BASE)
    revoked = dict(BASE, revoked=True)
    distinct = dict(BASE, id="unique", transport="bluetooth")
    for records in permutations([repeated, revoked, distinct]):
        result = visible_approved_devices(PRINCIPAL, list(records))
        assert [device["id"] for device in result] == ["unique"]


def test_three_records_with_same_identifier_are_all_denied():
    records = [
        dict(BASE),
        dict(BASE, approved=False),
        dict(BASE, school_id="school-b"),
    ]
    assert visible_approved_devices(PRINCIPAL, records) == []


def test_distinct_ids_are_returned_in_original_order():
    records = [
        dict(BASE, id="third"),
        dict(BASE, id="first"),
        dict(BASE, id="second"),
    ]
    assert [device["id"] for device in visible_approved_devices(
        PRINCIPAL, records
    )] == ["third", "first", "second"]
