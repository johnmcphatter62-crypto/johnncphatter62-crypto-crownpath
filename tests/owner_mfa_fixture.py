"""Real MFA enrollment for synthetic Owner HTTP fixtures; no gate overrides."""
import pyotp


def enroll_owner_for_test(client):
    identity = client.get("/api/auth/me")
    assert identity.status_code == 200, identity.text
    assert identity.json()["role"] == "OWNER"
    if identity.json().get("mfa_verification_required") is False:
        return
    assert identity.json()["permissions"] == []
    before = client.cookies.get("crownpath_session")
    setup = client.post("/api/auth/mfa/setup")
    assert setup.status_code == 200, setup.text
    enabled = client.post("/api/auth/mfa/enable", json={
        "code": pyotp.TOTP(setup.json()["secret"]).now(),
    })
    assert enabled.status_code == 200, enabled.text
    assert client.cookies.get("crownpath_session") != before
    verified = client.get("/api/auth/me")
    assert verified.status_code == 200, verified.text
    assert verified.json()["mfa_verification_required"] is False
    assert verified.json()["permissions"]
