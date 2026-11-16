"""Synthetic recovery approval expiry and replay policy.

This is an isolated policy test, not a production approval service.
"""
from datetime import datetime, timedelta, timezone

import pytest


def approve_recovery(approval, now, consumed_ids):
    if approval["expires_at"].tzinfo is None:
        raise PermissionError("Untrusted approval deadline")
    if now >= approval["expires_at"]:
        raise PermissionError("Approval expired")
    if approval["issued_at"] > now:
        raise PermissionError("Approval not yet valid")
    if approval["id"] in consumed_ids:
        raise PermissionError("Approval replay")
    consumed_ids.add(approval["id"])
    return True


NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _approval():
    return {
        "id": "fictional-approval-1",
        "issued_at": NOW - timedelta(minutes=2),
        "expires_at": NOW + timedelta(minutes=3),
    }


def test_fresh_approval_consumed_once():
    consumed = set()
    assert approve_recovery(_approval(), NOW, consumed)
    assert consumed == {"fictional-approval-1"}


def test_replayed_approval_rejected():
    consumed = set()
    approve_recovery(_approval(), NOW, consumed)
    with pytest.raises(PermissionError, match="replay"):
        approve_recovery(_approval(), NOW, consumed)


def test_expired_approval_rejected():
    approval = _approval()
    approval["expires_at"] = NOW
    with pytest.raises(PermissionError, match="expired"):
        approve_recovery(approval, NOW, set())


def test_future_issued_approval_rejected():
    approval = _approval()
    approval["issued_at"] = NOW + timedelta(minutes=1)
    with pytest.raises(PermissionError, match="not yet valid"):
        approve_recovery(approval, NOW, set())


def test_naive_expiry_rejected():
    approval = _approval()
    approval["expires_at"] = approval["expires_at"].replace(tzinfo=None)
    with pytest.raises(PermissionError, match="deadline"):
        approve_recovery(approval, NOW, set())
