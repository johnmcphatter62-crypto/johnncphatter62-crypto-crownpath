"""Instructor review authorization with real assignment lookup (mocked in tests)."""
from unittest.mock import patch

from crownpath.instructor_review_policy import can_review_assigned_learner


def user(role="INSTRUCTOR", active=True, user_id="instructor"):
    return {"role": role, "active": active, "user_id": user_id}


def test_assigned_instructor_with_manage_access_can_review():
    with patch("crownpath.resource_access.has_assignment", return_value=True) as lookup:
        assert can_review_assigned_learner(user(), "learner")
        lookup.assert_called_once_with("instructor", "LEARNER", "learner", "MANAGE")


def test_unassigned_instructor_is_denied():
    with patch("crownpath.resource_access.has_assignment", return_value=False):
        assert not can_review_assigned_learner(user(), "learner")


def test_inactive_instructor_is_denied_without_assignment_query():
    with patch("crownpath.resource_access.has_assignment") as lookup:
        assert not can_review_assigned_learner(user(active=False), "learner")
        lookup.assert_not_called()


def test_learner_cannot_review_even_with_assignment():
    with patch("crownpath.resource_access.has_assignment") as lookup:
        assert not can_review_assigned_learner(user(role="BARBER"), "learner")
        lookup.assert_not_called()


def test_self_review_denied_even_for_owner():
    assert not can_review_assigned_learner(user(role="OWNER", user_id="same"), "same")


def test_owner_can_review_other_learner():
    assert can_review_assigned_learner(user(role="OWNER"), "learner")


def test_missing_identity_denied():
    assert not can_review_assigned_learner(None, "learner")
    assert not can_review_assigned_learner(user(), "")
