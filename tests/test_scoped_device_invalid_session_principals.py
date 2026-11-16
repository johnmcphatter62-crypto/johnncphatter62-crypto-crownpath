"""Staged scoped device access rejects malformed session principals before DB use."""
import pytest

from crownpath.scoped_device_access import scoped_authorized_visible_devices

DEVICE = {"id": "device", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


class UnexpectedDatabaseUse:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("Invalid session must not query the database")


@pytest.mark.parametrize("principal", [
    None, True, 1, "learner", ["learner"], {},
    {"active": True},
    {"user_id": None, "active": True},
    {"user_id": "", "active": True},
    {"user_id": 123, "active": True},
    {"user_id": ["learner"], "active": True},
    {"user_id": {"id": "learner"}, "active": True},
    {"user_id": "learner"},
    {"user_id": "learner", "active": False},
    {"user_id": "learner", "active": 1},
    {"user_id": "learner", "active": "true"},
])
def test_invalid_session_denies_before_database_query(principal):
    assert scoped_authorized_visible_devices(
        UnexpectedDatabaseUse(), principal, [DEVICE]
    ) == []
