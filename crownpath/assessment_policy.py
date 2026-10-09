"""Pure CrownPath practical assessment policy.

No database writes or credential issuance. This policy evaluates a supplied
rubric and mandatory safety gates; instructor authorization must be checked
by the calling application before any result is persisted.
"""
from dataclasses import dataclass
from typing import Mapping


MINIMUM_COMPETENCY_SCORE = 3
MINIMUM_KNOWLEDGE_PERCENT = 80


@dataclass(frozen=True)
class AssessmentDecision:
    eligible_for_instructor_approval: bool
    failed_competencies: tuple[str, ...]
    failed_safety_gates: tuple[str, ...]
    knowledge_passed: bool


def evaluate_practical_assessment(
    competency_scores: Mapping[str, int],
    safety_gates: Mapping[str, bool],
    knowledge_percent: int,
) -> AssessmentDecision:
    if not competency_scores:
        raise ValueError("At least one competency score is required.")
    if not safety_gates:
        raise ValueError("At least one mandatory safety gate is required.")
    if isinstance(knowledge_percent, bool) or not isinstance(knowledge_percent, int) or not 0 <= knowledge_percent <= 100:
        raise ValueError("Knowledge percentage must be an integer from 0 to 100.")
    for name, score in competency_scores.items():
        if not name or isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 4:
            raise ValueError("Competency names and scores (1–4) are required.")
    for name, passed in safety_gates.items():
        if not name or not isinstance(passed, bool):
            raise ValueError("Safety gate names and boolean results are required.")

    failed_competencies = tuple(
        name for name, score in competency_scores.items()
        if score < MINIMUM_COMPETENCY_SCORE
    )
    failed_safety_gates = tuple(
        name for name, passed in safety_gates.items()
        if not passed
    )
    knowledge_passed = knowledge_percent >= MINIMUM_KNOWLEDGE_PERCENT
    eligible = not failed_competencies and not failed_safety_gates and knowledge_passed
    return AssessmentDecision(
        eligible_for_instructor_approval=eligible,
        failed_competencies=failed_competencies,
        failed_safety_gates=failed_safety_gates,
        knowledge_passed=knowledge_passed,
    )
