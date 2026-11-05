"""Synthetic recovery audit export permission separation tests.

No real user accounts, exports, or production endpoints are involved.
"""
import pytest


def authorize_export(principal):
    if not principal or not principal.get("authenticated"):
        raise PermissionError("Authentication required")
    if not principal.get("active"):
        raise PermissionError("Active account required")
    if principal.get("role") != "OWNER":
        raise PermissionError("Owner role required")
    if not principal.get("audit_export_permission"):
        raise PermissionError("Explicit audit export permission required")
    if not principal.get("recent_mfa"):
        raise PermissionError("Fresh MFA required")
    return True


def _owner(**changes):
    principal = {
        "authenticated": True, "active": True, "role": "OWNER",
        "audit_read_permission": True, "audit_export_permission": True,
        "recent_mfa": True,
    }
    principal.update(changes)
    return principal


def test_owner_with_explicit_export_permission_and_recent_mfa():
    assert authorize_export(_owner())


def test_audit_read_permission_alone_does_not_grant_export():
    with pytest.raises(PermissionError, match="Explicit audit export"):
        authorize_export(_owner(audit_export_permission=False))


@pytest.mark.parametrize("role", ["INSTRUCTOR", "COSMETOLOGY_PRO", "GUEST"])
def test_non_owner_roles_cannot_export(role):
    with pytest.raises(PermissionError, match="Owner role"):
        authorize_export(_owner(role=role))


def test_inactive_owner_cannot_export():
    with pytest.raises(PermissionError, match="Active account"):
        authorize_export(_owner(active=False))


def test_unauthenticated_request_cannot_export():
    with pytest.raises(PermissionError, match="Authentication"):
        authorize_export(None)


def test_owner_without_fresh_mfa_cannot_export():
    with pytest.raises(PermissionError, match="Fresh MFA"):
        authorize_export(_owner(recent_mfa=False))
