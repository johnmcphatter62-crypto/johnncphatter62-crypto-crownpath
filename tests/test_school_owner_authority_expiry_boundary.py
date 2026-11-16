"""Owner school authority must expire at, not after, its expiration instant."""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from crownpath.school_owner_authority import owner_authorized_for_school

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def test_owner_authorization_denied_at_exact_expiry_and_after():
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
                "CREATE TABLE school_owner_authorizations (authorization_id TEXT PRIMARY KEY, "
                "school_id TEXT NOT NULL, owner_user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
                "granted_at DATETIME NOT NULL, revoked_at DATETIME, expires_at DATETIME)"
            ))
            db.execute(sa.text(
                "INSERT INTO users VALUES ('owner', 'OWNER', TRUE)"
            ))
            db.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('grant', 'school-a', 'owner', TRUE, :granted, NULL, :expires)"
            ), {"granted": NOW - timedelta(days=1), "expires": NOW})

            assert owner_authorized_for_school(
                db, "owner", "school-a", now=NOW - timedelta(microseconds=1)
            ) is True
            assert owner_authorized_for_school(
                db, "owner", "school-a", now=NOW
            ) is False
            assert owner_authorized_for_school(
                db, "owner", "school-a", now=NOW + timedelta(seconds=1)
            ) is False
    finally:
        engine.dispose()
