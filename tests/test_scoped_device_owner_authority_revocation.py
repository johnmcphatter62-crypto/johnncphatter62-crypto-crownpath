"""Staged device access fails closed when the approving Owner loses authority."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
DEVICE = {"id": "approved", "owner_id": "learner", "school_id": "school-a",
          "approved": True, "revoked": False, "transport": "bluetooth"}


@pytest.mark.parametrize("change,params", [
    ("UPDATE school_owner_authorizations SET active = FALSE WHERE authorization_id = 'grant'", {}),
    ("UPDATE school_owner_authorizations SET revoked_at = :now WHERE authorization_id = 'grant'", {"now": NOW}),
    ("UPDATE school_owner_authorizations SET expires_at = :now WHERE authorization_id = 'grant'", {"now": NOW}),
    ("UPDATE users SET active = FALSE WHERE user_id = 'owner'", {}),
    ("UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'owner'", {}),
])
def test_owner_authority_removal_immediately_hides_devices(change, params):
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
            assert [device["id"] for device in scoped_authorized_visible_devices(
                db, principal, [DEVICE], now=NOW
            )] == ["approved"]
            db.execute(sa.text(change), params)
            assert scoped_authorized_visible_devices(
                db, principal, [DEVICE], now=NOW
            ) == []
    finally:
        engine.dispose()
