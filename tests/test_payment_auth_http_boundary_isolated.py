"""Isolated HTTP authentication boundary for future payment administration.

No payment route is mounted. This checks the existing FastAPI authentication
and permission dependency only; it does not prove payment-specific MFA/CSRF.
"""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import crownpath.main as main


def test_payment_permission_http_boundary_denies_untrusted_or_disabled_owner(monkeypatch):
    probe = FastAPI()
    calls = []

    @probe.post("/isolated/payment-config-probe")
    def payment_probe(user=Depends(main.require_permission("payments.configure"))):
        calls.append(user["role"])
        return {"allowed": True}

    # No trusted cookie/session identity: reject before any simulated change.
    with TestClient(probe) as client:
        response = client.post("/isolated/payment-config-probe")
        assert response.status_code == 401
        assert calls == []

        # A fabricated cookie must not establish authentication.
        response = client.post(
            "/isolated/payment-config-probe",
            cookies={"crownpath_session": "forged-session"},
        )
        assert response.status_code == 401
        assert calls == []

    # Current account status is authoritative even if a prior token decodes.
    monkeypatch.setattr(main, "decode_access_token", lambda token: "synthetic-owner")
    monkeypatch.setattr(main, "get_user_by_id", lambda uid: {
        "user_id": uid, "role": "OWNER", "active": False,
    })
    with TestClient(probe) as client:
        response = client.post(
            "/isolated/payment-config-probe",
            cookies={"crownpath_session": "previously-valid-test-token"},
        )
        assert response.status_code == 401
        assert calls == []
