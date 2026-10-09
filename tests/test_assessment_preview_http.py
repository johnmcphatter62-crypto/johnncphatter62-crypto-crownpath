"""HTTP-level security tests for CrownPath's read-only assessment preview."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from crownpath.main import app, current_user


def payload(**changes):
    data = {
        "knowledge_percent": 80,
        "competency_scores": {"consultation": 3},
        "safety_gates": {"sanitation": True},
    }
    data.update(changes)
    return data


def request_as(user, data=None):
    app.dependency_overrides[current_user] = lambda: user
    try:
        with TestClient(app) as client:
            return client.post(
                "/api/instructor/learners/learner/assessments/preview",
                json=payload() if data is None else data,
            )
    finally:
        app.dependency_overrides.pop(current_user, None)


@patch("crownpath.instructor_review_policy.can_review_assigned_learner", return_value=False)
def test_unassigned_reviewer_denied(_authorized):
    response = request_as({"user_id": "instructor", "role": "INSTRUCTOR", "active": True})
    assert response.status_code == 403


@patch("crownpath.instructor_review_policy.can_review_assigned_learner", return_value=True)
@patch("crownpath.main.get_user_by_id", return_value={"user_id": "learner", "role": "BARBER", "active": True})
def test_assigned_reviewer_receives_non_persistent_preview(_learner, _authorized):
    response = request_as({"user_id": "instructor", "role": "INSTRUCTOR", "active": True})
    assert response.status_code == 200
    body = response.json()
    assert body["preview_only"] is True
    assert body["approval_recorded"] is False
    assert body["eligible_for_instructor_approval"] is True


@patch("crownpath.instructor_review_policy.can_review_assigned_learner", return_value=True)
@patch("crownpath.main.get_user_by_id", return_value=None)
def test_missing_learner_denied(_learner, _authorized):
    response = request_as({"user_id": "instructor", "role": "INSTRUCTOR", "active": True})
    assert response.status_code == 404


@patch("crownpath.instructor_review_policy.can_review_assigned_learner", return_value=True)
@patch("crownpath.main.get_user_by_id", return_value={"user_id": "learner", "role": "BARBER", "active": True})
def test_failed_safety_gate_not_eligible(_learner, _authorized):
    response = request_as(
        {"user_id": "instructor", "role": "INSTRUCTOR", "active": True},
        payload(safety_gates={"sanitation": False}),
    )
    assert response.status_code == 200
    assert response.json()["eligible_for_instructor_approval"] is False
    assert response.json()["approval_recorded"] is False


@patch("crownpath.instructor_review_policy.can_review_assigned_learner", return_value=True)
@patch("crownpath.main.get_user_by_id", return_value={"user_id": "learner", "role": "BARBER", "active": True})
def test_out_of_range_score_rejected(_learner, _authorized):
    response = request_as(
        {"user_id": "instructor", "role": "INSTRUCTOR", "active": True},
        payload(competency_scores={"consultation": 5}),
    )
    assert response.status_code == 422
