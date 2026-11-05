"""Ambiguous school membership must fail closed for staged device visibility."""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
PRINCIPAL = {"user_id": "learner", "active": True}
DEVICES = [
    {"id": "a", "owner_id": "learner", "school_id": "school-a",
     "approved": True, "revoked": False, "transport": "wifi"},
    {"id": "b", "owner_id": "learner", "school_id": "school-b",
     "approved": True, "revoked": False, "transport": "bluetooth"},
]


def test_second_active_school_membership_denies_all_devices():
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
                "INSERT INTO users VALUES ('learner', 'BARBER', TRUE), "
                "('owner-a', 'OWNER', TRUE), ('owner-b', 'OWNER', TRUE)"
            ))
            db.execute(sa.text(
                "INSERT INTO schools VALUES ('school-a', TRUE), ('school-b', TRUE)"
            ))
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('m-a', 'school-a', 'learner', TRUE, 'owner-a', :approved, NULL)"
            ), {"approved": NOW - timedelta(hours=1)})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('g-a', 'school-a', 'owner-a', TRUE, :granted, NULL, NULL), "
                "('g-b', 'school-b', 'owner-b', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW - timedelta(days=1)})

            def visible():
                return scoped_authorized_visible_devices(db, PRINCIPAL, DEVICES, now=NOW)

            assert [device["id"] for device in visible()] == ["a"]
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('m-b', 'school-b', 'learner', TRUE, 'owner-b', :approved, NULL)"
            ), {"approved": NOW - timedelta(hours=1)})
            assert visible() == []

            db.execute(sa.text(
                "UPDATE school_memberships SET revoked_at = :revoked WHERE membership_id = 'm-b'"
            ), {"revoked": NOW})
            assert [device["id"] for device in visible()] == ["a"]
    finally:
        engine.dispose()
