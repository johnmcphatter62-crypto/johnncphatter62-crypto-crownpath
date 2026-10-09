"""Tests for CrownPath practical assessment policy."""
import pytest

from crownpath.assessment_policy import evaluate_practical_assessment


def evaluate(scores=None, safety=None, knowledge=80):
    return evaluate_practical_assessment(
        scores if scores is not None else {"consultation": 3, "sanitation": 3},
        safety if safety is not None else {"infection_control": True},
        knowledge,
    )


def test_eligible_requires_all_thresholds():
    result = evaluate()
    assert result.eligible_for_instructor_approval
    assert result.knowledge_passed


def test_low_competency_cannot_be_averaged_away():
    result = evaluate(scores={"consultation": 4, "sanitation": 2})
    assert not result.eligible_for_instructor_approval
    assert result.failed_competencies == ("sanitation",)


def test_failed_safety_gate_blocks_approval():
    result = evaluate(safety={"infection_control": False})
    assert not result.eligible_for_instructor_approval
    assert result.failed_safety_gates == ("infection_control",)


def test_knowledge_threshold():
    assert not evaluate(knowledge=79).eligible_for_instructor_approval
    assert evaluate(knowledge=80).eligible_for_instructor_approval


@pytest.mark.parametrize("scores,safety,knowledge", [
    ({}, {"safe": True}, 80),
    ({"skill": 3}, {}, 80),
    ({"skill": 0}, {"safe": True}, 80),
    ({"skill": 5}, {"safe": True}, 80),
    ({"skill": True}, {"safe": True}, 80),
    ({"skill": 3}, {"safe": 1}, 80),
    ({"skill": 3}, {"safe": True}, -1),
    ({"skill": 3}, {"safe": True}, 101),
    ({"skill": 3}, {"safe": True}, True),
])
def test_invalid_inputs_rejected(scores, safety, knowledge):
    with pytest.raises(ValueError):
        evaluate_practical_assessment(scores, safety, knowledge)
