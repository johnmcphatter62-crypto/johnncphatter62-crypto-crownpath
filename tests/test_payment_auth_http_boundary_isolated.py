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


def test_authenticated_non_owner_cannot_configure_payments_over_http(monkeypatch):
    """Synthetic authenticated learner must fail permission gate before side effects."""
    probe = FastAPI()
    changes = []

    @probe.post("/isolated/payment-config-probe")
    def payment_probe(user=Depends(main.require_permission("payments.configure"))):
        changes.append(user["user_id"])
        return {"allowed": True}

    monkeypatch.setattr(main, "decode_access_token", lambda token: "synthetic-learner")
    monkeypatch.setattr(main, "get_user_by_id", lambda uid: {
        "user_id": uid, "role": "COSMETOLOGY_PRO", "active": True,
        "mfa_enabled": True,
    })
    monkeypatch.setattr(main, "role_access_approved", lambda role: True)
    with TestClient(probe) as client:
        response = client.post(
            "/isolated/payment-config-probe",
            cookies={"crownpath_session": "synthetic-authenticated-session"},
        )
    assert response.status_code == 403
    assert changes == []


def test_owner_without_mfa_cannot_pass_payment_step_up_http_probe(monkeypatch):
    """Test-only step-up gate; production payment routes remain unimplemented."""
    from fastapi import HTTPException
    from crownpath.payment_access import can_configure_payments

    probe = FastAPI()
    changes = []

    @probe.post("/isolated/payment-step-up-probe")
    def payment_probe(user=Depends(main.require_permission("payments.configure"))):
        if not can_configure_payments(user, recent_mfa_verified=True):
            raise HTTPException(403, "Payment step-up required")
        changes.append(user["user_id"])
        return {"allowed": True}

    monkeypatch.setattr(main, "decode_access_token", lambda token: "synthetic-owner")
    monkeypatch.setattr(main, "get_user_by_id", lambda uid: {
        "user_id": uid, "role": "OWNER", "active": True,
        "mfa_enabled": False,
    })
    with TestClient(probe) as client:
        response = client.post(
            "/isolated/payment-step-up-probe",
            cookies={"crownpath_session": "synthetic-owner-session"},
        )
    assert response.status_code == 403
    assert changes == []


def test_mfa_enrolled_owner_without_fresh_payment_step_up_denied(monkeypatch):
    """Login MFA enrollment is not fresh payment-specific authorization."""
    from fastapi import HTTPException
    from crownpath.payment_access import can_configure_payments

    probe = FastAPI()
    changes = []

    @probe.post("/isolated/payment-step-up-probe")
    def payment_probe(user=Depends(main.require_permission("payments.configure"))):
        if not can_configure_payments(user, recent_mfa_verified=False):
            raise HTTPException(403, "Fresh payment MFA required")
        changes.append(user["user_id"])
        return {"allowed": True}

    monkeypatch.setattr(main, "decode_access_token", lambda token: "synthetic-owner")
    monkeypatch.setattr(main, "get_user_by_id", lambda uid: {
        "user_id": uid, "role": "OWNER", "active": True,
        "mfa_enabled": True,
    })
    with TestClient(probe) as client:
        response = client.post(
            "/isolated/payment-step-up-probe",
            cookies={"crownpath_session": "synthetic-owner-session"},
        )
    assert response.status_code == 403
    assert changes == []
