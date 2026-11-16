"""Database authorization errors must never reveal staged device records."""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
PRINCIPAL = {"user_id": "learner", "active": True}
DEVICE = {"id": "approved", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


class FailingConnection:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def execute(self, *_args, **_kwargs):
        self.calls += 1
        raise self.error


@pytest.mark.parametrize("error", [
    OperationalError("SELECT", {}, Exception("connection lost")),
    ProgrammingError("SELECT", {}, Exception("table missing")),
    TypeError("invalid database result"),
    ValueError("invalid database value"),
])
def test_database_authorization_failure_denies_devices(error):
    connection = FailingConnection(error)
    result = scoped_authorized_visible_devices(
        connection, PRINCIPAL, [DEVICE], now=NOW
    )
    assert result == []
    assert connection.calls == 1
