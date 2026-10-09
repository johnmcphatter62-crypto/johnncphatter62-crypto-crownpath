"""Assessment service transaction and authorization regression tests."""
from unittest.mock import patch

import pytest

from crownpath.assessment_service import (
    AssessmentEvidenceInvalid,
    AssessmentReviewDenied,
    submit_assessment_review,
)


class FakeSession:
    def __init__(self, fail_commit=False):
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = fail_commit

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("Simulated commit failure")

    def rollback(self):
        self.rollbacks += 1


def request(**changes):
    data = dict(
        reviewer={"user_id": "instructor", "role": "INSTRUCTOR", "active": True},
        learner_id="learner",
        lesson_id="consultation",
        rubric_version="v1",
        knowledge_percent=80,
        competency_scores={"consultation": 3},
        safety_gates={"sanitation": True},
        evidence=[{"type": "OBSERVATION_NOTE", "reference": "CP-EV-1", "observation_note": "Safe consultation."}],
    )
    data.update(changes)
    return data


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=True)
def test_approved_review_commits_assessment_and_audit(_auth, _owners):
    db = FakeSession()
    record = submit_assessment_review(db, **request())
    assert record.decision == "APPROVED"
    assert len(db.added) == 2
    assert db.commits == 1
    assert db.rollbacks == 0


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=True)
def test_failed_safety_gate_records_rejection(_auth, _owners):
    db = FakeSession()
    record = submit_assessment_review(db, **request(safety_gates={"sanitation": False}))
    assert record.decision == "REJECTED"
    assert db.commits == 1


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=False)
def test_unauthorized_reviewer_cannot_write(_auth, _owners):
    db = FakeSession()
    with pytest.raises(AssessmentReviewDenied):
        submit_assessment_review(db, **request())
    assert db.added == []
    assert db.commits == 0


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=True)
def test_invalid_evidence_cannot_write(_auth, _owners):
    db = FakeSession()
    with pytest.raises(AssessmentEvidenceInvalid):
        submit_assessment_review(db, **request(evidence=[]))
    assert db.added == []
    assert db.commits == 0


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=True)
def test_commit_failure_rolls_back(_auth, _owners):
    db = FakeSession(fail_commit=True)
    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        submit_assessment_review(db, **request())
    assert db.commits == 1
    assert db.rollbacks == 1


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=True)
def test_missing_trusted_ownership_denies_write(_auth, _owners):
    _owners.return_value = {}
    db = FakeSession()
    with pytest.raises(AssessmentEvidenceInvalid, match="ownership"):
        submit_assessment_review(db, **request())
    assert db.added == []
    assert db.commits == 0


@patch("crownpath.assessment_service.lookup_verified_evidence_owners", return_value={"CP-EV-1": "learner"})
@patch("crownpath.assessment_service.can_review_assigned_learner", return_value=True)
def test_wrong_learner_ownership_denies_write(_auth, _owners):
    _owners.return_value = {"CP-EV-1": "someone-else"}
    db = FakeSession()
    with pytest.raises(AssessmentEvidenceInvalid, match="ownership"):
        submit_assessment_review(db, **request())
    assert db.added == []
    assert db.commits == 0
