"""CrownPath academy permission regression tests.

These unit tests cover role permissions; endpoint ownership and practical
assessment authorization require separate integration tests.
"""
import pytest

from crownpath.permissions import has_permission, permissions_for_role


@pytest.mark.parametrize("role", ["OWNER", "INSTRUCTOR", "BARBER", "COSMETOLOGY_PRO", "HOME_CARE"])
def test_active_academy_roles_can_view(role):
    assert has_permission({"role": role, "active": True}, "academy.view")


@pytest.mark.parametrize("role", ["INSTRUCTOR", "BARBER", "COSMETOLOGY_PRO", "HOME_CARE"])
def test_non_owner_cannot_manage_entire_academy(role):
    assert not has_permission({"role": role, "active": True}, "academy.manage")


@pytest.mark.parametrize("role", ["OWNER", "INSTRUCTOR", "BARBER", "COSMETOLOGY_PRO", "HOME_CARE"])
def test_inactive_accounts_cannot_access_academy(role):
    assert not has_permission({"role": role, "active": False}, "academy.view")


def test_unknown_role_has_no_permissions():
    assert permissions_for_role("UNRECOGNIZED_ROLE") == set()
    assert not has_permission({"role": "UNRECOGNIZED_ROLE", "active": True}, "academy.view")


def test_missing_user_is_denied():
    assert not has_permission(None, "academy.view")


def test_instructor_permission_is_scoped():
    user = {"role": "INSTRUCTOR", "active": True}
    assert has_permission(user, "academy.manage_assigned")
    assert not has_permission(user, "academy.manage")
