"""Synthetic audit-export approval expiry and replay checks."""
from datetime import datetime, timedelta, timezone


def approve_once(approval, now):
    if now.tzinfo is None:
        raise ValueError("UTC-aware timestamp required")
    if approval["used"] or now >= approval["expires_at"]:
        return False
    approval["used"] = True
    return True


def test_approval_is_one_time():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    approval = {"used": False, "expires_at": now + timedelta(minutes=5)}
    assert approve_once(approval, now)
    assert not approve_once(approval, now)


def test_expired_approval_is_denied():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    approval = {"used": False, "expires_at": now - timedelta(seconds=1)}
    assert not approve_once(approval, now)
    assert approval["used"] is False


def test_exact_expiration_boundary_is_denied():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    approval = {"used": False, "expires_at": now}
    assert not approve_once(approval, now)
