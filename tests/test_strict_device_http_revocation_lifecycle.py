"""Test-only HTTP lifecycle: approval revocation must take effect on next request.

No CrownPath production route, device scan, or live session is created.
"""
import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from crownpath.strict_device_access import strict_authorized_visible_devices


def test_approval_revocation_takes_effect_on_next_http_request():
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    try:
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
                "('owner', 'OWNER', TRUE)"
            ))
            conn.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
            conn.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('membership', 'school-a', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
            ))

        app = FastAPI()
        trusted_principal = {"user_id": "learner", "active": True}
        device = {"id": "wifi-1", "owner_id": "learner", "school_id": "school-a",
                  "approved": True, "revoked": False, "transport": "wifi"}

        def server_principal():
            return trusted_principal

        @app.get("/test-only/devices")
        def list_devices(principal=Depends(server_principal)):
            with engine.connect() as conn:
                return {"devices": strict_authorized_visible_devices(conn, principal, [device])}

        client = TestClient(app)
        first = client.get("/test-only/devices")
        assert first.status_code == 200
        assert [item["id"] for item in first.json()["devices"]] == ["wifi-1"]

        with engine.begin() as conn:
            conn.execute(sa.text(
                "UPDATE school_memberships SET revoked_at = '2026-11-04' "
                "WHERE membership_id = 'membership'"
            ))

        second = client.get("/test-only/devices")
        assert second.status_code == 200
        assert second.json() == {"devices": []}

        with engine.begin() as conn:
            conn.execute(sa.text(
                "UPDATE school_memberships SET revoked_at = NULL, approved_by_user_id = NULL "
                "WHERE membership_id = 'membership'"
            ))
        third = client.get("/test-only/devices")
        assert third.status_code == 200
        assert third.json() == {"devices": []}
    finally:
        engine.dispose()
