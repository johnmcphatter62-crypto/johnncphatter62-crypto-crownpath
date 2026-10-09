"""Evidence ownership and database constraint contract tests."""
import pytest
from sqlalchemy import CheckConstraint

from crownpath.evidence_ownership import validate_evidence_ownership
from crownpath.models import PracticalAssessment


@pytest.mark.parametrize("refs,owners,expected", [
    (["ev-1"], {"ev-1": "learner"}, True),
    (["ev-1", "ev-2"], {"ev-1": "learner", "ev-2": "learner"}, True),
    (["ev-1"], {"ev-1": "other"}, False),
    (["ev-1"], {}, False),
    (["ev-1", "ev-1"], {"ev-1": "learner"}, False),
    ([], {}, False),
])
def test_evidence_owner_policy(refs, owners, expected):
    assert validate_evidence_ownership("learner", refs, owners) is expected


def test_assessment_model_has_database_check_constraints():
    constraints = {
        item.name for item in PracticalAssessment.__table__.constraints
        if isinstance(item, CheckConstraint)
    }
    assert {
        "ck_practical_assessment_knowledge_range",
        "ck_practical_assessment_decision",
        "ck_practical_assessment_distinct_reviewer",
    } <= constraints
