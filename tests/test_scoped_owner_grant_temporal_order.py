"""Security regression: later Owner grants must not validate older approvals.

These tests are expected to reveal a staged policy gap until the resolver is
updated. Disposable SQLite only; no production app or hardware changes.
"""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.scoped_owner_school import scoped_owner_school_id


NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def _school_for(*, grant_time, approval_time):
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
                "('membership', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
            ), {"approved": approval_time})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('grant', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
            ), {"granted": grant_time})
            return scoped_owner_school_id(
                db, {"user_id": "learner", "active": True}, now=NOW
            )
    finally:
        engine.dispose()


def test_grant_before_approval_permits_current_membership():
    assert _school_for(
        grant_time=NOW - timedelta(days=2),
        approval_time=NOW - timedelta(days=1),
    ) == "school-a"


def test_grant_after_approval_must_not_retroactively_validate_membership():
    assert _school_for(
        grant_time=NOW - timedelta(hours=1),
        approval_time=NOW - timedelta(days=1),
    ) is None


def test_grant_at_approval_instant_is_valid():
    approved = NOW - timedelta(days=1)
    assert _school_for(grant_time=approved, approval_time=approved) == "school-a"
