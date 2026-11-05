"""Test-only device visibility respects the original school approval timeline."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices


NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
APPROVED = NOW - timedelta(days=1)
DEVICE = {"id": "camera", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


@pytest.mark.parametrize("grant_offset,expected", [
    (timedelta(days=-2), ["camera"]),
    (timedelta(days=-1), ["camera"]),
    (timedelta(hours=-1), []),
    (timedelta(hours=1), []),
])
def test_device_visibility_requires_grant_before_membership_approval(
    grant_offset, expected
):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as db:
            db.execute(sa.text(
                "CREATE TABLE users (user_id TEXT PRIMARY KEY, role TEXT NOT NULL, active BOOLEAN NOT NULL)"
            ))
            db.execute(sa.text(
                "CREATE TABLE schools (school_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"
            ))
            db.execute(sa.text(
                "CREATE TABLE school_memberships (membership_id TEXT PRIMARY KEY, "
                "school_id TEXT NOT NULL, user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
                "approved_by_user_id TEXT, approved_at DATETIME, revoked_at DATETIME)"
            ))
            db.execute(sa.text(
                "CREATE TABLE school_owner_authorizations (authorization_id TEXT PRIMARY KEY, "
                "school_id TEXT NOT NULL, owner_user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
                "granted_at DATETIME NOT NULL, revoked_at DATETIME, expires_at DATETIME)"
            ))
            db.execute(sa.text(
                "INSERT INTO users VALUES ('learner', 'BARBER', TRUE), ('owner', 'OWNER', TRUE)"
            ))
            db.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('m', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
            ), {"approved": APPROVED})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('g', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW + grant_offset})
            devices = scoped_authorized_visible_devices(
                db, {"user_id": "learner", "active": True}, [DEVICE], now=NOW
            )
            assert [device["id"] for device in devices] == expected
    finally:
        engine.dispose()
