"""Test-only HTTP integration of strict device authorization.

This does not add any endpoint to CrownPath's actual application.
The principal is injected by the harness, never supplied by the request.
"""
import pytest
import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from crownpath.strict_device_access import strict_authorized_visible_devices


@pytest.fixture
def db():
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
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
            "('owner', 'OWNER', TRUE), ('stranger', 'COSMETOLOGY_PRO', TRUE)"
        ))
        conn.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('membership', 'school-a', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
        ))
    yield engine
    engine.dispose()


DEVICES = [
    {"id": "own", "owner_id": "learner", "school_id": "school-a",
     "approved": True, "revoked": False, "transport": "wifi"},
    {"id": "other", "owner_id": "stranger", "school_id": "school-a",
     "approved": True, "revoked": False, "transport": "bluetooth"},
]


def client_for(engine, *, enabled=False, principal=None):
    app = FastAPI()

    def get_principal():
        if principal is None:
            raise HTTPException(401, "Authentication required")
        return principal

    @app.get("/internal-test/devices")
    def list_devices(user=Depends(get_principal)):
        if not enabled:
            raise HTTPException(404, "Feature disabled")
        with engine.connect() as conn:
            return {"devices": strict_authorized_visible_devices(conn, user, DEVICES)}

    return TestClient(app)


def test_disabled_endpoint_never_exposes_data(db):
    response = client_for(db, principal={"user_id": "learner", "active": True}).get(
        "/internal-test/devices"
    )
    assert response.status_code == 404


def test_enabled_endpoint_requires_authenticated_principal(db):
    assert client_for(db, enabled=True).get("/internal-test/devices").status_code == 401


def test_enabled_endpoint_shows_only_own_approved_device(db):
    response = client_for(
        db, enabled=True, principal={"user_id": "learner", "active": True}
    ).get("/internal-test/devices")
    assert response.status_code == 200
    assert [d["id"] for d in response.json()["devices"]] == ["own"]


def test_query_cannot_impersonate_other_user_or_school(db):
    response = client_for(
        db, enabled=True, principal={"user_id": "stranger", "active": True}
    ).get("/internal-test/devices?user_id=learner&school_id=school-a&role=OWNER")
    assert response.status_code == 200
    assert response.json() == {"devices": []}


@pytest.mark.parametrize("sql", [
    "UPDATE users SET active = FALSE WHERE user_id = 'owner'",
    "UPDATE school_memberships SET revoked_at = '2026-11-04'",
    "UPDATE school_memberships SET approved_by_user_id = 'stranger'",
])
def test_revoked_or_invalid_owner_approval_denies_http_data(db, sql):
    with db.begin() as conn:
        conn.execute(sa.text(sql))
    response = client_for(
        db, enabled=True, principal={"user_id": "learner", "active": True}
    ).get("/internal-test/devices")
    assert response.status_code == 200
    assert response.json() == {"devices": []}
