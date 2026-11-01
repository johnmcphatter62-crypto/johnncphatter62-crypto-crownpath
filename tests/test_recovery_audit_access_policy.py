"""Synthetic recovery audit access policy tests.

No production users, sessions, or security records are accessed.
"""
import pytest


AUDIT = (
    {"actor_id": "fictional-owner", "backup_id": "fictional-backup",
     "outcome": "denied", "reason_code": "approval-required"},
)


def read_recovery_audit(principal, records=AUDIT):
    if not principal or not principal.get("authenticated"):
        raise PermissionError("Authentication required")
    if not principal.get("active"):
        raise PermissionError("Active account required")
    if principal.get("role") != "Owner":
        raise PermissionError("Owner role required")
    if not principal.get("audit_read_permission"):
        raise PermissionError("Audit permission required")
    return tuple(dict(record) for record in records)


def _owner(**changes):
    principal = {"authenticated": True, "active": True,
                 "role": "Owner", "audit_read_permission": True}
    principal.update(changes)
    return principal


def test_authorized_owner_can_read_audit():
    assert read_recovery_audit(_owner()) == AUDIT


@pytest.mark.parametrize("role", ["Learner", "Instructor", "Guest"])
def test_other_roles_cannot_read_audit(role):
    with pytest.raises(PermissionError, match="Owner role"):
        read_recovery_audit(_owner(role=role))


def test_inactive_owner_cannot_read_audit():
    with pytest.raises(PermissionError, match="Active account"):
        read_recovery_audit(_owner(active=False))


def test_owner_without_audit_permission_cannot_read():
    with pytest.raises(PermissionError, match="Audit permission"):
        read_recovery_audit(_owner(audit_read_permission=False))


def test_unauthenticated_request_cannot_read_audit():
    with pytest.raises(PermissionError, match="Authentication"):
        read_recovery_audit(None)


def test_returned_records_do_not_modify_stored_audit():
    result = read_recovery_audit(_owner())
    result[0]["outcome"] = "success"
    assert AUDIT[0]["outcome"] == "denied"
