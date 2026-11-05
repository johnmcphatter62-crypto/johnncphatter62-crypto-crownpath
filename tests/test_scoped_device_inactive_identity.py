"""Staged school-scoped device visibility fails closed on inactive identities."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
DEVICE = {"id": "approved", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "bluetooth"}


@pytest.mark.parametrize("change", [
    "UPDATE users SET active = FALSE WHERE user_id = 'learner'",
    "UPDATE schools SET active = FALSE WHERE school_id = 'school-a'",
    "UPDATE school_memberships SET active = FALSE WHERE membership_id = 'member'",
    "UPDATE school_memberships SET revoked_at = '2026-11-05' WHERE membership_id = 'member'",
])
def test_inactive_learner_school_or_membership_denies_devices(change):
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
                "('member', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
            ), {"approved": NOW - timedelta(days=1)})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('grant', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW - timedelta(days=2)})
            principal = {"user_id": "learner", "active": True}
            before = scoped_authorized_visible_devices(db, principal, [DEVICE], now=NOW)
            assert [device["id"] for device in before] == ["approved"]
            db.execute(sa.text(change))
            after = scoped_authorized_visible_devices(db, principal, [DEVICE], now=NOW)
            assert after == []
    finally:
        engine.dispose()
