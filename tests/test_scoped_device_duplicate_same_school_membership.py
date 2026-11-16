"""Duplicate approved memberships in one school must deny staged device access."""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
DEVICE = {"id": "approved", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "wifi"}


def test_duplicate_membership_same_school_denies_until_duplicate_revoked():
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
                "INSERT INTO school_owner_authorizations VALUES "
                "('g', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW - timedelta(days=2)})
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('m-1', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
            ), {"approved": NOW - timedelta(days=1)})

            def visible():
                return scoped_authorized_visible_devices(
                    db, {"user_id": "learner", "active": True}, [DEVICE], now=NOW
                )

            assert [device["id"] for device in visible()] == ["approved"]
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('m-2', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
            ), {"approved": NOW - timedelta(hours=1)})
            assert visible() == []
            db.execute(sa.text(
                "UPDATE school_memberships SET active = FALSE WHERE membership_id = 'm-2'"
            ))
            assert [device["id"] for device in visible()] == ["approved"]
    finally:
        engine.dispose()
