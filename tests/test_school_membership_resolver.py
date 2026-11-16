"""Database-backed authorization tests; disposable in-memory SQLite only."""
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

from crownpath.school_membership import verified_school_id


@pytest.fixture
def db():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE users (user_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"
        ))
        connection.execute(sa.text(
            "CREATE TABLE schools (school_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"
        ))
        connection.execute(sa.text(
            "CREATE TABLE school_memberships (membership_id TEXT PRIMARY KEY, "
            "school_id TEXT NOT NULL, user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
            "approved_by_user_id TEXT, approved_at TEXT, revoked_at TEXT)"
        ))
        connection.execute(sa.text(
            "INSERT INTO users VALUES ('learner-1', TRUE), ('learner-2', TRUE)"
        ))
        connection.execute(sa.text(
            "INSERT INTO schools VALUES ('school-1', TRUE), ('school-2', TRUE)"
        ))
        yield connection
    engine.dispose()


def grant(db, membership_id="member-1", school_id="school-1", user_id="learner-1",
          active=True, approved_by="owner-1", approved_at="2026-11-04",
          revoked_at=None):
    db.execute(sa.text(
        "INSERT INTO school_memberships VALUES (:mid, :sid, :uid, :active, "
        ":approver, :approved_at, :revoked_at)"
    ), {"mid": membership_id, "sid": school_id, "uid": user_id,
        "active": active, "approver": approved_by,
        "approved_at": approved_at, "revoked_at": revoked_at})


def test_approved_active_membership(db):
    grant(db)
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) == "school-1"


def test_no_membership_fails_closed(db):
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) is None


@pytest.mark.parametrize("change", [
    {"active": False}, {"approved_by": None}, {"approved_at": None},
    {"revoked_at": "2026-11-04"},
])
def test_unapproved_inactive_or_revoked_membership_denied(db, change):
    grant(db, **change)
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) is None


def test_inactive_school_denied(db):
    grant(db)
    db.execute(sa.text("UPDATE schools SET active = FALSE WHERE school_id = 'school-1'"))
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) is None


def test_inactive_user_denied(db):
    grant(db)
    db.execute(sa.text("UPDATE users SET active = FALSE WHERE user_id = 'learner-1'"))
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) is None


def test_two_active_school_memberships_ambiguous(db):
    grant(db)
    grant(db, membership_id="member-2", school_id="school-2")
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) is None


def test_other_learners_membership_not_visible(db):
    grant(db, user_id="learner-2")
    assert verified_school_id(db, {"user_id": "learner-1", "active": True}) is None


@pytest.mark.parametrize("principal", [
    None, {}, {"user_id": "", "active": True},
    {"user_id": "learner-1", "active": False},
    {"user_id": "learner-1", "active": 1},
])
def test_invalid_principal_denied(db, principal):
    grant(db)
    assert verified_school_id(db, principal) is None


def test_client_school_claim_ignored(db):
    grant(db)
    principal = {"user_id": "learner-1", "active": True, "school_id": "school-2"}
    assert verified_school_id(db, principal) == "school-1"


def test_missing_tables_fails_closed():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            assert verified_school_id(connection, {"user_id": "learner-1", "active": True}) is None
    finally:
        engine.dispose()
