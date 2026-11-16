"""Isolated database-backed tests for strict device access composition."""
import pytest
import sqlalchemy as sa

from crownpath.strict_device_access import strict_authorized_visible_devices


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
            "approved_by_user_id TEXT, approved_at TEXT, revoked_at TEXT)"
        ))
        conn.execute(sa.text(
            "INSERT INTO users VALUES ('learner', 'COSMETOLOGY_PRO', TRUE), "
            "('other', 'COSMETOLOGY_PRO', TRUE), ('owner', 'OWNER', TRUE), "
            "('instructor', 'INSTRUCTOR', TRUE)"
        ))
        conn.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE), ('school-b', TRUE)"))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('membership-a', 'school-a', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
        ))
        yield conn
    engine.dispose()


@pytest.fixture
def devices():
    return [
        {"id": "allowed", "owner_id": "learner", "school_id": "school-a",
         "approved": True, "revoked": False, "transport": "bluetooth"},
        {"id": "other-school", "owner_id": "learner", "school_id": "school-b",
         "approved": True, "revoked": False, "transport": "wifi"},
        {"id": "other-owner", "owner_id": "other", "school_id": "school-a",
         "approved": True, "revoked": False, "transport": "wifi"},
        {"id": "revoked", "owner_id": "learner", "school_id": "school-a",
         "approved": True, "revoked": True, "transport": "wifi"},
        {"id": "unapproved", "owner_id": "learner", "school_id": "school-a",
         "approved": False, "revoked": False, "transport": "wifi"},
    ]


def visible_ids(db, devices, principal=None):
    if principal is None:
        principal = {"user_id": "learner", "active": True}
    return [d["id"] for d in strict_authorized_visible_devices(db, principal, devices)]


def test_only_owner_approved_own_school_device_visible(db, devices):
    assert visible_ids(db, devices) == ["allowed"]


def test_client_school_claim_does_not_expand_scope(db, devices):
    assert visible_ids(db, devices, {"user_id": "learner", "active": True,
                                      "school_id": "school-b"}) == ["allowed"]


@pytest.mark.parametrize("statement", [
    "UPDATE users SET active = FALSE WHERE user_id = 'owner'",
    "UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'owner'",
    "UPDATE school_memberships SET approved_by_user_id = 'instructor'",
    "UPDATE school_memberships SET approved_at = NULL",
    "UPDATE school_memberships SET revoked_at = '2026-11-04'",
    "UPDATE school_memberships SET active = FALSE",
    "UPDATE schools SET active = FALSE WHERE school_id = 'school-a'",
    "UPDATE users SET active = FALSE WHERE user_id = 'learner'",
])
def test_revoked_or_invalid_approval_hides_devices(db, devices, statement):
    db.execute(sa.text(statement))
    assert visible_ids(db, devices) == []


def test_multiple_owner_approved_schools_fail_closed(db, devices):
    db.execute(sa.text(
        "INSERT INTO school_memberships VALUES "
        "('membership-b', 'school-b', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
    ))
    assert visible_ids(db, devices) == []


def test_other_learner_cannot_borrow_school_scope(db, devices):
    assert visible_ids(db, devices, {"user_id": "other", "active": True}) == []


@pytest.mark.parametrize("principal", [
    None, {}, {"user_id": "learner", "active": False},
    {"user_id": "learner", "active": 1},
])
def test_invalid_identity_denied(db, devices, principal):
    assert strict_authorized_visible_devices(db, principal, devices) == []


def test_database_error_denies_access(devices):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as conn:
            assert strict_authorized_visible_devices(
                conn, {"user_id": "learner", "active": True}, devices
            ) == []
    finally:
        engine.dispose()
