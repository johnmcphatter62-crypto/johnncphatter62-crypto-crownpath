"""Disposable integration: device record approval and revocation are fail-closed."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.scoped_device_access import scoped_authorized_visible_devices

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
BASE = {"id": "device-a", "owner_id": "learner", "school_id": "school-a",
        "approved": True, "revoked": False, "transport": "wifi"}


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
            "INSERT INTO users VALUES ('learner', 'BARBER', TRUE), ('owner', 'OWNER', TRUE)"
        ))
        conn.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('m', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
        ), {"approved": NOW - timedelta(days=1)})
        conn.execute(sa.text(
            "INSERT INTO school_owner_authorizations VALUES "
            "('g', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
        ), {"granted": NOW - timedelta(days=2)})
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def visible(db, device):
    return scoped_authorized_visible_devices(
        db, {"user_id": "learner", "active": True}, [device], now=NOW
    )


@pytest.mark.parametrize("field,value", [
    ("approved", False),
    ("approved", None),
    ("approved", "true"),
    ("revoked", True),
    ("revoked", None),
    ("revoked", "false"),
    ("transport", "unknown"),
    ("school_id", "school-b"),
    ("owner_id", "another-learner"),
])
def test_device_record_change_immediately_hides_device(db, field, value):
    device = dict(BASE)
    assert [item["id"] for item in visible(db, device)] == ["device-a"]
    device[field] = value
    assert visible(db, device) == []


def test_revocation_does_not_change_other_approved_devices(db):
    first = dict(BASE)
    second = dict(BASE, id="device-b", transport="bluetooth")
    assert [d["id"] for d in scoped_authorized_visible_devices(
        db, {"user_id": "learner", "active": True}, [first, second], now=NOW
    )] == ["device-a", "device-b"]
    first["revoked"] = True
    assert [d["id"] for d in scoped_authorized_visible_devices(
        db, {"user_id": "learner", "active": True}, [first, second], now=NOW
    )] == ["device-b"]
