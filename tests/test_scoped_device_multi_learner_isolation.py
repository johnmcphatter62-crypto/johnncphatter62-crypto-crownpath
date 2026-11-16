"""Staged multi-learner device isolation using disposable SQLite."""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def test_device_changes_for_one_learner_do_not_expose_another():
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
                "INSERT INTO users VALUES ('learner-a', 'BARBER', TRUE), "
                "('learner-b', 'BARBER', TRUE), ('owner', 'OWNER', TRUE)"
            ))
            db.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('m-a', 'school-a', 'learner-a', TRUE, 'owner', :approved, NULL), "
                "('m-b', 'school-a', 'learner-b', TRUE, 'owner', :approved, NULL)"
            ), {"approved": NOW - timedelta(days=1)})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('grant', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW - timedelta(days=2)})
            devices = [
                {"id": "device-a", "owner_id": "learner-a", "school_id": "school-a",
                 "approved": True, "revoked": False, "transport": "wifi"},
                {"id": "device-b", "owner_id": "learner-b", "school_id": "school-a",
                 "approved": True, "revoked": False, "transport": "bluetooth"},
            ]

            def ids(user_id):
                return [item["id"] for item in scoped_authorized_visible_devices(
                    db, {"user_id": user_id, "active": True}, devices, now=NOW
                )]

            assert ids("learner-a") == ["device-a"]
            assert ids("learner-b") == ["device-b"]
            devices[0]["revoked"] = True
            assert ids("learner-a") == []
            assert ids("learner-b") == ["device-b"]
            devices[0]["revoked"] = False
            devices[1]["approved"] = False
            assert ids("learner-a") == ["device-a"]
            assert ids("learner-b") == []
            devices[1]["owner_id"] = "learner-a"
            devices[1]["approved"] = True
            assert ids("learner-a") == ["device-a", "device-b"]
            assert ids("learner-b") == []
    finally:
        engine.dispose()
