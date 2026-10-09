"""Tests for instructor review authorization policy."""
import pytest

from crownpath.instructor_review_policy import can_review_learner


@pytest.mark.parametrize("role", ["BARBER", "COSMETOLOGY_PRO", "HOME_CARE"])
def test_learner_roles_cannot_approve(role):
    assert not can_review_learner({"user_id": "user1", "role": role, "active": True}, "user2", {"user2"})


def test_instructor_can_review_assigned_learner():
    assert can_review_learner({"user_id": "teacher", "role": "INSTRUCTOR", "active": True}, "learner", {"learner"})


def test_instructor_cannot_review_unassigned_learner():
    assert not can_review_learner({"user_id": "teacher", "role": "INSTRUCTOR", "active": True}, "learner", set())


def test_inactive_instructor_cannot_review():
    assert not can_review_learner({"user_id": "teacher", "role": "INSTRUCTOR", "active": False}, "learner", {"learner"})


def test_self_review_is_forbidden_even_for_owner():
    assert not can_review_learner({"user_id": "same", "role": "OWNER", "active": True}, "same", {"same"})


def test_owner_can_review_other_learner():
    assert can_review_learner({"user_id": "owner", "role": "OWNER", "active": True}, "learner", set())


def test_missing_identity_or_user_is_denied():
    assert not can_review_learner(None, "learner", {"learner"})
    assert not can_review_learner({"role": "INSTRUCTOR", "active": True}, "learner", {"learner"})
    assert not can_review_learner({"user_id": "teacher", "role": "INSTRUCTOR", "active": True}, "", {"learner"})
