"""Synthetic recovery authorization policy; no actual restore operation."""
import pytest


def authorize_recovery(actor, backup, approval):
    if not actor.get("active") or actor.get("role") != "OWNER":
        raise PermissionError("Active owner required")
    if not actor.get("mfa_verified"):
        raise PermissionError("Owner verification required")
    if approval.get("actor_id") != actor.get("id"):
        raise PermissionError("Approval owner mismatch")
    if approval.get("backup_id") != backup.get("id"):
        raise PermissionError("Approval backup mismatch")
    if approval.get("target") != backup.get("target"):
        raise PermissionError("Approval target mismatch")
    if approval.get("used"):
        raise PermissionError("Approval already used")
    return True


OWNER = {"id": "owner-1", "role": "OWNER", "active": True, "mfa_verified": True}
BACKUP = {"id": "sample-backup", "target": "test"}
APPROVAL = {"actor_id": "owner-1", "backup_id": "sample-backup", "target": "test", "used": False}


def test_verified_owner_approval():
    assert authorize_recovery(OWNER, BACKUP, APPROVAL)


@pytest.mark.parametrize("actor", [
    {**OWNER, "role": "LEARNER"},
    {**OWNER, "active": False},
    {**OWNER, "mfa_verified": False},
])
def test_unauthorized_actor_denied(actor):
    with pytest.raises(PermissionError):
        authorize_recovery(actor, BACKUP, APPROVAL)


@pytest.mark.parametrize("approval", [
    {**APPROVAL, "actor_id": "other-owner"},
    {**APPROVAL, "backup_id": "other-backup"},
    {**APPROVAL, "target": "production"},
    {**APPROVAL, "used": True},
])
def test_invalid_approval_denied(approval):
    with pytest.raises(PermissionError):
        authorize_recovery(OWNER, BACKUP, approval)
