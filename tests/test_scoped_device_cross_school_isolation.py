"""Cross-school device records remain isolated under staged scoped policy."""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def test_cross_school_device_cannot_be_seen_by_learner_with_valid_home_school():
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
                "('m', 'school-a', 'learner', TRUE, 'owner-a', :approved, NULL)"
            ), {"approved": NOW - timedelta(days=1)})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('g-a', 'school-a', 'owner-a', TRUE, :granted, NULL, NULL), "
                "('g-b', 'school-b', 'owner-b', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW - timedelta(days=2)})
            devices = [
                {"id": "home", "owner_id": "learner", "school_id": "school-a",
                 "approved": True, "revoked": False, "transport": "wifi"},
                {"id": "foreign", "owner_id": "learner", "school_id": "school-b",
                 "approved": True, "revoked": False, "transport": "bluetooth"},
            ]
            principal = {"user_id": "learner", "active": True,
                         "school_id": "school-b", "role": "OWNER"}
            def ids():
                return [d["id"] for d in scoped_authorized_visible_devices(
                    db, principal, devices, now=NOW
                )]
            assert ids() == ["home"]
            devices[0]["revoked"] = True
            assert ids() == []
            devices[1]["school_id"] = "school-a"
            assert ids() == ["foreign"]
    finally:
        engine.dispose()
