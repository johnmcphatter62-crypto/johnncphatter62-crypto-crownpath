"""Test-only HTTP integration for school-scoped device authorization.

No endpoint is registered on the CrownPath production application.
"""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from crownpath.scoped_device_access import scoped_authorized_visible_devices


NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def test_http_visibility_tracks_owner_school_authority_without_client_override():
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
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
                "('member', 'school-a', 'learner', TRUE, 'owner', :approved, NULL)"
            ), {"approved": NOW - timedelta(hours=1)})
            db.execute(sa.text(
                "INSERT INTO school_owner_authorizations VALUES "
                "('grant', 'school-a', 'owner', TRUE, :granted, NULL, NULL)"
            ), {"granted": NOW - timedelta(days=1)})

        devices = [{"id": "own", "owner_id": "learner", "school_id": "school-a",
                    "approved": True, "revoked": False, "transport": "wifi"}]
        app = FastAPI()
        authenticated = {"user_id": "learner", "active": True}

        def principal():
            if authenticated is None:
                raise HTTPException(401, "Authentication required")
            return authenticated

        @app.get("/test-only/scoped-devices")
        def list_devices(user=Depends(principal)):
            with engine.connect() as db:
                return {"devices": scoped_authorized_visible_devices(
                    db, user, devices, now=NOW
                )}

        with TestClient(app) as client:
            path = "/test-only/scoped-devices?user_id=owner&school_id=other&role=OWNER"
            first = client.get(path)
            assert first.status_code == 200
            assert [device["id"] for device in first.json()["devices"]] == ["own"]

            with engine.begin() as db:
                db.execute(sa.text(
                    "UPDATE school_owner_authorizations SET revoked_at = :revoked "
                    "WHERE authorization_id = 'grant'"
                ), {"revoked": NOW})
            assert client.get(path).json() == {"devices": []}

            with engine.begin() as db:
                db.execute(sa.text(
                    "UPDATE school_owner_authorizations SET revoked_at = NULL, active = FALSE "
                    "WHERE authorization_id = 'grant'"
                ))
            assert client.get(path).json() == {"devices": []}

            with engine.begin() as db:
                db.execute(sa.text(
                    "UPDATE school_owner_authorizations SET active = TRUE "
                    "WHERE authorization_id = 'grant'"
                ))
            assert [device["id"] for device in client.get(path).json()["devices"]] == ["own"]
    finally:
        engine.dispose()
