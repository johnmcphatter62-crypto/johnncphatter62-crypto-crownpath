"""Malformed device owner and school identifiers must fail closed."""
import pytest

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "device", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("invalid_owner", [
    None, 0, 1, True, "", ["learner"], {"id": "learner"}, ("learner",),
])
def test_invalid_owner_id_never_matches_authenticated_user(invalid_owner):
    malformed = dict(DEVICE, id="bad-owner", owner_id=invalid_owner)
    result = visible_approved_devices(PRINCIPAL, [malformed, DEVICE])
    assert [record["id"] for record in result] == ["device"]


@pytest.mark.parametrize("invalid_school", [
    None, 0, 1, True, "", ["school-a"], {"id": "school-a"}, ("school-a",),
])
def test_invalid_school_id_never_matches_authenticated_school(invalid_school):
    malformed = dict(DEVICE, id="bad-school", school_id=invalid_school)
    result = visible_approved_devices(PRINCIPAL, [malformed, DEVICE])
    assert [record["id"] for record in result] == ["device"]


@pytest.mark.parametrize("invalid_principal_id", [
    None, 0, 1, True, "", ["learner"], {"id": "learner"},
])
def test_invalid_principal_user_id_denies_all(invalid_principal_id):
    principal = dict(PRINCIPAL, user_id=invalid_principal_id)
    assert visible_approved_devices(principal, [DEVICE]) == []


@pytest.mark.parametrize("invalid_principal_school", [
    None, 0, 1, True, "", ["school-a"], {"id": "school-a"},
])
def test_invalid_principal_school_id_denies_all(invalid_principal_school):
    principal = dict(PRINCIPAL, school_id=invalid_principal_school)
    assert visible_approved_devices(principal, [DEVICE]) == []
