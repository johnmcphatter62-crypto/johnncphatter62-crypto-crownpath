"""Strict school resolver tests using a disposable in-memory database."""
import pytest
import sqlalchemy as sa

from crownpath.verified_owner_school import verified_owner_school_id


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
            "('owner', 'OWNER', TRUE), ('instructor', 'INSTRUCTOR', TRUE)"
        ))
        conn.execute(sa.text(
            "INSERT INTO schools VALUES ('school-a', TRUE), ('school-b', TRUE)"
        ))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('member-a', 'school-a', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
        ))
        yield conn
    engine.dispose()


def principal(**changes):
    return {"user_id": "learner", "active": True, **changes}


def test_valid_owner_approved_membership(db):
    assert verified_owner_school_id(db, principal()) == "school-a"


@pytest.mark.parametrize("statement", [
    "UPDATE users SET active = FALSE WHERE user_id = 'owner'",
    "UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'owner'",
    "UPDATE school_memberships SET approved_by_user_id = 'instructor'",
    "UPDATE school_memberships SET approved_by_user_id = NULL",
    "UPDATE school_memberships SET approved_at = NULL",
    "UPDATE school_memberships SET revoked_at = '2026-11-04'",
    "UPDATE school_memberships SET active = FALSE",
    "UPDATE schools SET active = FALSE WHERE school_id = 'school-a'",
    "UPDATE users SET active = FALSE WHERE user_id = 'learner'",
])
def test_invalid_owner_or_membership_denied(db, statement):
    db.execute(sa.text(statement))
    assert verified_owner_school_id(db, principal()) is None


def test_multiple_valid_memberships_denied(db):
    db.execute(sa.text(
        "INSERT INTO school_memberships VALUES "
        "('member-b', 'school-b', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
    ))
    assert verified_owner_school_id(db, principal()) is None


def test_client_claimed_school_cannot_override_database(db):
    assert verified_owner_school_id(db, principal(school_id="school-b")) == "school-a"


@pytest.mark.parametrize("identity", [
    None, {}, {"user_id": "learner", "active": False},
    {"user_id": "learner", "active": 1},
    {"user_id": "", "active": True},
    {"user_id": "someone-else", "active": True},
])
def test_invalid_principal_denied(db, identity):
    assert verified_owner_school_id(db, identity) is None


def test_missing_schema_fails_closed():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as conn:
            assert verified_owner_school_id(conn, principal()) is None
    finally:
        engine.dispose()
