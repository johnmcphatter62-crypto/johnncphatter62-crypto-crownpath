"""Isolated SQLite tests for school membership Owner approval."""
import pytest
import sqlalchemy as sa

from crownpath.school_approval import owner_approved_membership


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
            "INSERT INTO users VALUES "
            "('learner', 'COSMETOLOGY_PRO', TRUE), "
            "('owner', 'OWNER', TRUE), "
            "('instructor', 'INSTRUCTOR', TRUE)"
        ))
        conn.execute(sa.text("INSERT INTO schools VALUES ('school', TRUE)"))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('membership', 'school', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
        ))
        yield conn
    engine.dispose()


def test_active_owner_approval_valid(db):
    assert owner_approved_membership(db, "membership") is True


@pytest.mark.parametrize("statement", [
    "UPDATE users SET active = FALSE WHERE user_id = 'owner'",
    "UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'owner'",
    "UPDATE school_memberships SET approved_by_user_id = 'instructor'",
    "UPDATE school_memberships SET approved_by_user_id = 'missing'",
    "UPDATE school_memberships SET approved_by_user_id = NULL",
    "UPDATE school_memberships SET approved_at = NULL",
    "UPDATE school_memberships SET active = FALSE",
    "UPDATE school_memberships SET revoked_at = '2026-11-04'",
    "UPDATE schools SET active = FALSE",
    "UPDATE users SET active = FALSE WHERE user_id = 'learner'",
])
def test_invalid_or_revoked_approval_denied(db, statement):
    db.execute(sa.text(statement))
    assert owner_approved_membership(db, "membership") is False


@pytest.mark.parametrize("membership_id", [None, "", 1, "unknown"])
def test_missing_or_invalid_membership_denied(db, membership_id):
    assert owner_approved_membership(db, membership_id) is False


def test_missing_schema_denied():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as conn:
            assert owner_approved_membership(conn, "membership") is False
    finally:
        engine.dispose()
