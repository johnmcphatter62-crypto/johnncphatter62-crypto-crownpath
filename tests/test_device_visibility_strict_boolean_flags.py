"""Device approval and revocation must use exact Boolean values."""
import pytest

from crownpath.device_visibility import visible_approved_devices

PRINCIPAL = {"user_id": "learner", "school_id": "school-a", "active": True}
DEVICE = {"id": "device", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("invalid_approved", [1, 0, "true", "false", None, [], {}])
def test_approval_requires_literal_true(invalid_approved):
    record = dict(DEVICE, approved=invalid_approved)
    assert visible_approved_devices(PRINCIPAL, [record]) == []


@pytest.mark.parametrize("invalid_revoked", [1, 0, "true", "false", None, [], {}])
def test_revocation_requires_literal_false(invalid_revoked):
    record = dict(DEVICE, revoked=invalid_revoked)
    assert visible_approved_devices(PRINCIPAL, [record]) == []


@pytest.mark.parametrize("invalid_active", [1, 0, "true", "false", None, [], {}])
def test_principal_active_requires_literal_true(invalid_active):
    principal = dict(PRINCIPAL, active=invalid_active)
    assert visible_approved_devices(principal, [DEVICE]) == []


def test_exact_booleans_allow_only_approved_not_revoked():
    records = [
        dict(DEVICE, id="allowed"),
        dict(DEVICE, id="not-approved", approved=False),
        dict(DEVICE, id="revoked", revoked=True),
    ]
    assert [record["id"] for record in visible_approved_devices(
        PRINCIPAL, records
    )] == ["allowed"]
