"""Reject malformed device identifiers while preserving unique valid records."""
import pytest

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "valid", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("bad_id", [
    None, "", 0, 1, True, False, ["valid"], {"id": "valid"}, ("valid",),
])
def test_malformed_device_id_is_rejected_without_hiding_valid_record(bad_id):
    malformed = dict(DEVICE, id=bad_id)
    result = visible_approved_devices(PRINCIPAL, [malformed, DEVICE])
    assert [record["id"] for record in result] == ["valid"]


def test_duplicate_valid_id_is_denied_even_when_one_record_is_unapproved():
    duplicate = dict(DEVICE, approved=False)
    assert visible_approved_devices(PRINCIPAL, [DEVICE, duplicate]) == []


def test_distinct_valid_ids_remain_visible_with_malformed_records_present():
    second = dict(DEVICE, id="second", transport="bluetooth")
    malformed = dict(DEVICE, id={"unexpected": "value"})
    result = visible_approved_devices(PRINCIPAL, [DEVICE, malformed, second])
    assert [record["id"] for record in result] == ["valid", "second"]
