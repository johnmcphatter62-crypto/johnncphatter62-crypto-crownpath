"""Orchestration for instructor-reviewed practical assessments.

No HTTP route or credential issuance. Assignment lookup is server-side.
The supplied SQLAlchemy session owns one atomic assessment+audit transaction.
"""
from crownpath.assessment_evidence import validate_assessment_evidence
from crownpath.assessment_policy import evaluate_practical_assessment
from crownpath.assessment_repository import stage_assessment_review
from crownpath.instructor_review_policy import can_review_assigned_learner
from crownpath.evidence_ownership import validate_evidence_ownership


class AssessmentReviewDenied(PermissionError):
    pass


class AssessmentEvidenceInvalid(ValueError):
    pass


def submit_assessment_review(
    db,
    *,
    reviewer: dict,
    learner_id: str,
    lesson_id: str,
    rubric_version: str,
    knowledge_percent: int,
    competency_scores: dict[str, int],
    safety_gates: dict[str, bool],
    evidence: list[dict],
    trusted_evidence_owners: dict[str, str] | None = None,
    review_note: str | None = None,
):
    if not can_review_assigned_learner(reviewer, learner_id):
        raise AssessmentReviewDenied("Reviewer is not authorized for this learner.")
    if not evidence:
        raise AssessmentEvidenceInvalid("At least one evidence record is required.")
    for item in evidence:
        evidence_type = item.get("type") if isinstance(item, dict) else None
        result = validate_assessment_evidence(
            item, require_consent=evidence_type in {"PHOTO", "VIDEO"}
        )
        if not result.valid:
            raise AssessmentEvidenceInvalid("; ".join(result.errors))
    references = [item["reference"] for item in evidence]
    if not validate_evidence_ownership(learner_id, references, trusted_evidence_owners or {}):
        raise AssessmentEvidenceInvalid("Evidence ownership could not be verified.")
    evaluation = evaluate_practical_assessment(
        competency_scores, safety_gates, knowledge_percent
    )
    decision = "APPROVED" if evaluation.eligible_for_instructor_approval else "REJECTED"
    try:
        assessment = stage_assessment_review(
            db,
            learner_id=learner_id,
            reviewer_id=reviewer["user_id"],
            lesson_id=lesson_id,
            rubric_version=rubric_version,
            knowledge_percent=knowledge_percent,
            competency_scores=competency_scores,
            safety_gates=safety_gates,
            evidence_refs=references,
            decision=decision,
            review_note=review_note,
        )
        db.commit()
        return assessment
    except Exception:
        db.rollback()
        raise
