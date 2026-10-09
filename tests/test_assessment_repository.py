"""Unit tests for transaction staging; no production schema migration."""
import pytest

from crownpath.assessment_repository import stage_assessment_review
from crownpath.models import AuditEvent, PracticalAssessment


class FakeSession:
    def __init__(self):
        self.added = []
    def add(self, item):
        self.added.append(item)


def payload(**changes):
    data = dict(
        learner_id="learner", reviewer_id="instructor",
        lesson_id="consultation", rubric_version="v1",
        knowledge_percent=80, competency_scores={"consultation": 3},
        safety_gates={"sanitation": True}, evidence_refs=["CP-EV-1"],
        decision="REVIEW_REQUIRED",
    )
    data.update(changes)
    return data


def test_assessment_and_audit_are_staged_together_without_commit():
    db = FakeSession()
    assessment = stage_assessment_review(db, **payload())
    assert len(db.added) == 2
    assert isinstance(db.added[0], PracticalAssessment)
    assert isinstance(db.added[1], AuditEvent)
    assert db.added[1].resource_id == assessment.assessment_id
    assert assessment.learner_id == "learner"
    assert assessment.reviewer_id == "instructor"


@pytest.mark.parametrize("changes", [
    {"reviewer_id": "learner"},
    {"learner_id": ""},
    {"lesson_id": ""},
    {"rubric_version": ""},
    {"decision": "ISSUED_LICENSE"},
])
def test_invalid_review_is_not_staged(changes):
    db = FakeSession()
    with pytest.raises(ValueError):
        stage_assessment_review(db, **payload(**changes))
    assert db.added == []
