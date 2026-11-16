"""Malformed authorization clocks must fail closed before querying membership."""
from datetime import datetime, timezone

import pytest

from crownpath.scoped_device_access import scoped_authorized_visible_devices

PRINCIPAL = {"user_id": "learner", "active": True}
DEVICE = {"id": "device", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


class UnexpectedDatabaseUse:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("Invalid clock must not query the database")


@pytest.mark.parametrize("bad_now", [
    None, "2026-11-05T12:00:00Z", 0, 1, True, [], {},
    datetime(2026, 11, 5, 12),
])
def test_invalid_explicit_clock_denies_without_database_access(bad_now):
    if bad_now is None:
        pytest.skip("None means use the current UTC time by design")
    assert scoped_authorized_visible_devices(
        UnexpectedDatabaseUse(), PRINCIPAL, [DEVICE], now=bad_now
    ) == []


def test_aware_datetime_reaches_database_authorization_check():
    class DatabaseWasQueried(Exception):
        pass

    class TrackingDatabase:
        def execute(self, *_args, **_kwargs):
            raise DatabaseWasQueried

    # The staged resolver intentionally catches only known DB/value errors.
    with pytest.raises(DatabaseWasQueried):
        scoped_authorized_visible_devices(
            TrackingDatabase(), PRINCIPAL, [DEVICE],
            now=datetime(2026, 11, 5, 12, tzinfo=timezone.utc),
        )
