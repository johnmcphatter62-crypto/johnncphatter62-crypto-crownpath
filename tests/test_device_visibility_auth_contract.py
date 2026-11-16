"""Guard against enabling device discovery before authenticated school scope exists.

CrownPath's current auth._user_dict does not include a verified school_id.
The visibility policy must fail closed rather than infer tenant ownership.
"""
from types import SimpleNamespace

from crownpath.auth import _user_dict
from crownpath.device_visibility import visible_approved_devices


def test_current_auth_identity_has_no_verified_school_scope():
    row = SimpleNamespace(
        user_id="synthetic-learner",
        name="Test Learner",
        email="test@example.invalid",
        password_hash="not-a-real-hash",
        role="BARBER",
        track="BARBER",
        active=True,
        email_verified=False,
        mfa_enabled=False,
        mfa_secret=None,
        failed_login_attempts=0,
        locked_until=None,
        last_login_at=None,
        created_at=None,
    )
    principal = _user_dict(row)
    assert "school_id" not in principal
    devices = [{
        "id": "synthetic-device", "owner_id": principal["user_id"],
        "school_id": "synthetic-school", "approved": True,
        "revoked": False, "transport": "bluetooth",
    }]
    assert visible_approved_devices(principal, devices) == []


def test_client_claimed_school_does_not_change_verified_principal():
    principal = {"user_id": "synthetic-learner", "active": True}
    client_payload = {"school_id": "synthetic-school"}
    devices = [{
        "id": "synthetic-device", "owner_id": "synthetic-learner",
        "school_id": client_payload["school_id"], "approved": True,
        "revoked": False, "transport": "wifi",
    }]
    assert visible_approved_devices(principal, devices) == []
