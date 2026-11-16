"""Integration tests for the actual CrownPath device access composition.

Disposable SQLite data only. No HTTP endpoint, hardware, or production access.
"""
import pytest
import sqlalchemy as sa

from crownpath.device_access import authorized_visible_devices


@pytest.fixture
def connection():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as db:
        db.execute(sa.text("CREATE TABLE users (user_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"))
        db.execute(sa.text("CREATE TABLE schools (school_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"))
        db.execute(sa.text(
            "CREATE TABLE school_memberships (membership_id TEXT PRIMARY KEY, "
            "school_id TEXT NOT NULL, user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
            "approved_by_user_id TEXT, approved_at TEXT, revoked_at TEXT)"
        ))
        db.execute(sa.text("INSERT INTO users VALUES ('learner-1', TRUE), ('learner-2', TRUE)"))
        db.execute(sa.text("INSERT INTO schools VALUES ('school-1', TRUE), ('school-2', TRUE)"))
        db.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('membership-1', 'school-1', 'learner-1', TRUE, 'owner-1', '2026-11-04', NULL)"
        ))
        yield db
    engine.dispose()


@pytest.fixture
def devices():
    return [
        {"id": "own-approved", "owner_id": "learner-1", "school_id": "school-1",
         "approved": True, "revoked": False, "transport": "wifi"},
        {"id": "other-learner", "owner_id": "learner-2", "school_id": "school-1",
         "approved": True, "revoked": False, "transport": "bluetooth"},
        {"id": "other-school", "owner_id": "learner-1", "school_id": "school-2",
         "approved": True, "revoked": False, "transport": "wifi"},
        {"id": "revoked", "owner_id": "learner-1", "school_id": "school-1",
         "approved": True, "revoked": True, "transport": "bluetooth"},
        {"id": "unapproved", "owner_id": "learner-1", "school_id": "school-1",
         "approved": False, "revoked": False, "transport": "wifi"},
    ]


def test_only_own_approved_device_visible(connection, devices):
    result = authorized_visible_devices(connection, {"user_id": "learner-1", "active": True}, devices)
    assert [device["id"] for device in result] == ["own-approved"]


def test_forged_school_id_cannot_expand_visibility(connection, devices):
    result = authorized_visible_devices(
        connection, {"user_id": "learner-1", "school_id": "school-2", "active": True}, devices
    )
    assert [device["id"] for device in result] == ["own-approved"]


def test_other_learner_cannot_borrow_membership(connection, devices):
    assert authorized_visible_devices(connection, {"user_id": "learner-2", "active": True}, devices) == []


@pytest.mark.parametrize("principal", [
    None, {}, {"user_id": "learner-1", "active": False},
    {"user_id": "learner-1", "active": 1},
    {"user_id": "", "active": True},
])
def test_missing_or_inactive_principal_denied(connection, devices, principal):
    assert authorized_visible_devices(connection, principal, devices) == []


def test_membership_revocation_immediately_hides_devices(connection, devices):
    principal = {"user_id": "learner-1", "active": True}
    assert len(authorized_visible_devices(connection, principal, devices)) == 1
    connection.execute(sa.text(
        "UPDATE school_memberships SET revoked_at = '2026-11-04' "
        "WHERE membership_id = 'membership-1'"
    ))
    assert authorized_visible_devices(connection, principal, devices) == []


def test_ambiguous_membership_hides_devices(connection, devices):
    connection.execute(sa.text(
        "INSERT INTO school_memberships VALUES "
        "('membership-2', 'school-2', 'learner-1', TRUE, 'owner-1', '2026-11-04', NULL)"
    ))
    assert authorized_visible_devices(connection, {"user_id": "learner-1", "active": True}, devices) == []


def test_missing_schema_fails_closed(devices):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as db:
            assert authorized_visible_devices(db, {"user_id": "learner-1", "active": True}, devices) == []
    finally:
        engine.dispose()
