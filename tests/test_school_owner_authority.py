"""Disposable SQLite tests of the staged school Owner authority policy."""
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from crownpath.school_owner_authority import owner_authorized_for_school


NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)


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
            "CREATE TABLE school_owner_authorizations (authorization_id TEXT PRIMARY KEY, "
            "school_id TEXT NOT NULL, owner_user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
            "granted_at DATETIME NOT NULL, revoked_at DATETIME, expires_at DATETIME)"
        ))
        conn.execute(sa.text(
            "INSERT INTO users VALUES ('owner-a', 'OWNER', TRUE), "
            "('owner-b', 'OWNER', TRUE), ('learner', 'BARBER', TRUE)"
        ))
        conn.execute(sa.text(
            "INSERT INTO schools VALUES ('school-a', TRUE), ('school-b', TRUE)"
        ))
        conn.execute(sa.text(
            "INSERT INTO school_owner_authorizations VALUES "
            "('grant-a', 'school-a', 'owner-a', TRUE, :granted, NULL, :expires)"
        ), {"granted": NOW - timedelta(days=1), "expires": NOW + timedelta(days=1)})
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def test_matching_active_owner_grant(db):
    assert owner_authorized_for_school(db, "owner-a", "school-a", now=NOW)


def test_cross_school_owner_is_denied(db):
    assert not owner_authorized_for_school(db, "owner-a", "school-b", now=NOW)
    assert not owner_authorized_for_school(db, "owner-b", "school-a", now=NOW)


@pytest.mark.parametrize("statement", [
    "UPDATE users SET active = FALSE WHERE user_id = 'owner-a'",
    "UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'owner-a'",
    "UPDATE schools SET active = FALSE WHERE school_id = 'school-a'",
    "UPDATE school_owner_authorizations SET active = FALSE WHERE authorization_id = 'grant-a'",
    "UPDATE school_owner_authorizations SET revoked_at = '2026-11-04' WHERE authorization_id = 'grant-a'",
])
def test_inactive_or_revoked_grant_is_denied(db, statement):
    db.execute(sa.text(statement))
    db.commit()
    assert not owner_authorized_for_school(db, "owner-a", "school-a", now=NOW)


def test_expired_grant_is_denied(db):
    assert not owner_authorized_for_school(
        db, "owner-a", "school-a", now=NOW + timedelta(days=2)
    )


def test_future_grant_is_denied(db):
    assert not owner_authorized_for_school(
        db, "owner-a", "school-a", now=NOW - timedelta(days=2)
    )


@pytest.mark.parametrize("owner,school", [
    ("", "school-a"), ("owner-a", ""), (None, "school-a"),
    ("owner-a", None), (["owner-a"], "school-a"),
])
def test_malformed_identity_denied(db, owner, school):
    assert not owner_authorized_for_school(db, owner, school, now=NOW)


def test_naive_timestamp_denied(db):
    assert not owner_authorized_for_school(
        db, "owner-a", "school-a", now=datetime(2026, 11, 5)
    )


def test_missing_authorization_table_denied():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as conn:
            assert not owner_authorized_for_school(
                conn, "owner-a", "school-a", now=NOW
            )
    finally:
        engine.dispose()
