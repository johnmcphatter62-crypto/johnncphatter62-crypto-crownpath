"""Approved records from another school must not cross the school boundary."""
from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "local", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


def test_foreign_school_device_is_hidden_despite_matching_owner_and_approval():
    foreign = dict(DEVICE, id="foreign", school_id="school-b")
    result = visible_approved_devices(PRINCIPAL, [foreign, DEVICE])
    assert [device["id"] for device in result] == ["local"]


def test_school_switch_does_not_reuse_approval_from_other_school():
    foreign = dict(DEVICE, id="foreign", school_id="school-b")
    for school_id, expected in [
        ("school-a", ["local"]), ("school-b", ["foreign"]),
        ("school-c", []),
    ]:
        principal = dict(PRINCIPAL, school_id=school_id)
        assert [record["id"] for record in visible_approved_devices(
            principal, [DEVICE, foreign]
        )] == expected


def test_foreign_duplicate_identifier_blocks_ambiguous_local_record():
    foreign = dict(DEVICE, school_id="school-b")
    assert visible_approved_devices(PRINCIPAL, [DEVICE, foreign]) == []


def test_foreign_record_cannot_override_local_revocation():
    local_revoked = dict(DEVICE, revoked=True)
    foreign = dict(DEVICE, id="foreign", school_id="school-b")
    assert visible_approved_devices(PRINCIPAL, [local_revoked, foreign]) == []
