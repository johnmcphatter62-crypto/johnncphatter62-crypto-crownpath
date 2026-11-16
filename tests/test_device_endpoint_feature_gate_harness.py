"""Test-only FastAPI harness. No route is added to the CrownPath application.

The isolated endpoint must remain unavailable unless a test explicitly opts in.
Even when enabled, it requires an authenticated server-side principal.
"""
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient


def build_harness(*, feature_enabled=False, principal=None):
    app = FastAPI()

    def authenticated_principal():
        if principal is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return principal

    @app.get("/internal-test/devices")
    def test_devices(user=Depends(authenticated_principal)):
        if not feature_enabled:
            raise HTTPException(status_code=404, detail="Feature unavailable")
        if user.get("active") is not True:
            raise HTTPException(status_code=403, detail="Inactive account")
        return {"devices": []}

    return TestClient(app)


def test_feature_is_unavailable_by_default_even_for_authenticated_user():
    client = build_harness(principal={"user_id": "learner", "active": True})
    response = client.get("/internal-test/devices")
    assert response.status_code == 404
    assert "devices" not in response.json()


def test_unauthenticated_request_cannot_access_test_endpoint():
    client = build_harness()
    assert client.get("/internal-test/devices").status_code == 401


def test_explicit_test_enable_still_requires_authentication():
    client = build_harness(feature_enabled=True)
    assert client.get("/internal-test/devices").status_code == 401


def test_inactive_user_denied_when_test_enabled():
    client = build_harness(
        feature_enabled=True, principal={"user_id": "learner", "active": False}
    )
    assert client.get("/internal-test/devices").status_code == 403


def test_enabled_harness_returns_no_device_data():
    client = build_harness(
        feature_enabled=True, principal={"user_id": "learner", "active": True}
    )
    response = client.get("/internal-test/devices")
    assert response.status_code == 200
    assert response.json() == {"devices": []}


@pytest.mark.parametrize("claimed_scope", [
    {"school_id": "other-school"}, {"user_id": "owner"},
    {"role": "OWNER"}, {"active": "true"},
])
def test_request_parameters_cannot_activate_disabled_feature(claimed_scope):
    client = build_harness(principal={"user_id": "learner", "active": True})
    assert client.get("/internal-test/devices", params=claimed_scope).status_code == 404
