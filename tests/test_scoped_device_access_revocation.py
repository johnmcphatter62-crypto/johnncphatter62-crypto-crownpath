"""Disposable SQLite integration tests of staged school-scoped device visibility."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
PRINCIPAL = {"user_id": "learner", "active": True}
DEVICES = [
    {"id": "own", "owner_id": "learner", "school_id": "school-a",
     "approved": True, "revoked": False, "transport": "wifi"},
    {"id": "other-school", "owner_id": "learner", "school_id": "school-b",
     "approved": True, "revoked": False, "transport": "bluetooth"},
    {"id": "other-user", "owner_id": "other", "school_id": "school-a",
     "approved": True, "revoked": False, "transport": "wifi"},
]


@pytest.fixture
def db():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE users (user_id TEXT PRIMARY KEY, role TEXT NOT NULL, active BOOLEAN NOT NULL)"
        ))
        conn.execute(sa.text(
            "CREATE TABLE schools (school_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"
        ))
        conn.execute(sa.text(
            "CREATE TABLE school_memberships (membership_id TEXT PRIMARY KEY, "
            "school_id TEXT NOT NULL, user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
            "approved_by_user_id TEXT, approved_at DATETIME, revoked_at DATETIME)"
        ))
        conn.execute(sa.text(
            "CREATE TABLE school_owner_authorizations (authorization_id TEXT PRIMARY KEY, "
            "school_id TEXT NOT NULL, owner_user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
            "granted_at DATETIME NOT NULL, revoked_at DATETIME, expires_at DATETIME)"
        ))
        conn.execute(sa.text(
            "INSERT INTO users VALUES ('learner', 'BARBER', TRUE), "
            "('owner-a', 'OWNER', TRUE), ('owner-b', 'OWNER', TRUE)"
        ))
        conn.execute(sa.text(
            "INSERT INTO schools VALUES ('school-a', TRUE), ('school-b', TRUE)"
        ))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('member', 'school-a', 'learner', TRUE, 'owner-a', :approved, NULL)"
        ), {"approved": NOW - timedelta(hours=1)})
        conn.execute(sa.text(
            "INSERT INTO school_owner_authorizations VALUES "
            "('grant', 'school-a', 'owner-a', TRUE, :granted, NULL, :expires)"
        ), {"granted": NOW - timedelta(days=1), "expires": NOW + timedelta(days=1)})
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def visible(db, *, now=NOW, principal=PRINCIPAL):
    return scoped_authorized_visible_devices(db, principal, DEVICES, now=now)


def test_only_own_same_school_approved_device_is_visible(db):
    assert [device["id"] for device in visible(db)] == ["own"]


@pytest.mark.parametrize("statement", [
    "UPDATE school_owner_authorizations SET revoked_at = '2026-11-05'",
    "UPDATE school_owner_authorizations SET active = FALSE",
    "UPDATE school_owner_authorizations SET school_id = 'school-b'",
    "UPDATE school_memberships SET approved_by_user_id = 'owner-b'",
    "UPDATE users SET active = FALSE WHERE user_id = 'owner-a'",
    "UPDATE schools SET active = FALSE WHERE school_id = 'school-a'",
])
def test_school_owner_authority_loss_removes_device_visibility(db, statement):
    assert [device["id"] for device in visible(db)] == ["own"]
    db.execute(sa.text(statement))
    db.commit()
    assert visible(db) == []


def test_expired_grant_removes_visibility(db):
    assert [device["id"] for device in visible(db)] == ["own"]
    assert visible(db, now=NOW + timedelta(days=2)) == []


def test_claimed_school_cannot_override_database(db):
    principal = {"user_id": "learner", "active": True, "school_id": "school-b"}
    assert [device["id"] for device in visible(db, principal=principal)] == ["own"]


def test_unverified_principal_fails_closed(db):
    assert visible(db, principal={"user_id": "learner", "active": False}) == []
