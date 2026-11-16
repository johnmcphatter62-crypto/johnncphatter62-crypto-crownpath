"""An inactive principal must not retain staged device visibility."""
from crownpath.device_visibility import visible_approved_devices

DEVICE = {"id": "device", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


def test_deactivation_denies_previously_visible_device():
    principal = {"user_id": "learner", "school_id": "school-a", "active": True}
    assert [record["id"] for record in visible_approved_devices(
        principal, [DEVICE]
    )] == ["device"]

    principal["active"] = False
    assert visible_approved_devices(principal, [DEVICE]) == []


def test_reactivation_does_not_override_revoked_device():
    principal = {"user_id": "learner", "school_id": "school-a", "active": False}
    revoked = dict(DEVICE, revoked=True)
    assert visible_approved_devices(principal, [revoked]) == []

    principal["active"] = True
    assert visible_approved_devices(principal, [revoked]) == []


def test_missing_active_flag_denies_access():
    principal = {"user_id": "learner", "school_id": "school-a"}
    assert visible_approved_devices(principal, [DEVICE]) == []
