"""Disposable SQLite tests for school-scoped learner membership approval."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.scoped_owner_school import scoped_owner_school_id

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


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
            "('membership', 'school-a', 'learner', TRUE, 'owner-a', :approved, NULL)"
        ), {"approved": NOW - timedelta(hours=1)})
        conn.execute(sa.text(
            "INSERT INTO school_owner_authorizations VALUES "
            "('grant', 'school-a', 'owner-a', TRUE, :granted, NULL, :expires)"
        ), {"granted": NOW - timedelta(days=1), "expires": NOW + timedelta(days=1)})
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def resolve(db):
    return scoped_owner_school_id(
        db, {"user_id": "learner", "active": True}, now=NOW
    )


def test_valid_matching_owner_school_membership(db):
    assert resolve(db) == "school-a"


@pytest.mark.parametrize("statement", [
    "UPDATE school_memberships SET approved_by_user_id = 'owner-b'",
    "UPDATE school_owner_authorizations SET school_id = 'school-b'",
    "UPDATE school_owner_authorizations SET revoked_at = '2026-11-04'",
    "UPDATE school_owner_authorizations SET active = FALSE",
    "UPDATE users SET active = FALSE WHERE user_id = 'owner-a'",
    "UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'owner-a'",
    "UPDATE school_memberships SET revoked_at = '2026-11-04'",
    "UPDATE school_memberships SET approved_at = NULL",
    "UPDATE schools SET active = FALSE WHERE school_id = 'school-a'",
])
def test_missing_or_invalid_scoped_approval_denied(db, statement):
    db.execute(sa.text(statement))
    db.commit()
    assert resolve(db) is None


def test_duplicate_active_memberships_fail_closed(db):
    db.execute(sa.text(
        "INSERT INTO school_memberships VALUES "
        "('membership-2', 'school-b', 'learner', TRUE, 'owner-b', :approved, NULL)"
    ), {"approved": NOW - timedelta(hours=1)})
    db.commit()
    assert resolve(db) is None


def test_expired_owner_grant_denied(db):
    assert scoped_owner_school_id(
        db, {"user_id": "learner", "active": True}, now=NOW + timedelta(days=2)
    ) is None


def test_client_claimed_school_ignored(db):
    assert scoped_owner_school_id(
        db, {"user_id": "learner", "active": True, "school_id": "school-b"}, now=NOW
    ) == "school-a"


@pytest.mark.parametrize("principal", [
    None, {}, {"user_id": "learner", "active": False},
    {"user_id": "", "active": True},
    {"user_id": "learner", "active": "true"},
])
def test_invalid_principal_denied(db, principal):
    assert scoped_owner_school_id(db, principal, now=NOW) is None


def test_missing_tables_fail_closed():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as conn:
            assert scoped_owner_school_id(
                conn, {"user_id": "learner", "active": True}, now=NOW
            ) is None
    finally:
        engine.dispose()
