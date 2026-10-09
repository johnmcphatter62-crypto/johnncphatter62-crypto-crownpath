"""Persistence helpers for CrownPath practical assessment records.

The caller is responsible for authentication, assignment authorization,
validated evidence, and evaluation. Never call commit here: assessment and
audit event must be committed by the caller in one transaction.
"""
import json
import uuid

from crownpath.models import AuditEvent, PracticalAssessment


def stage_assessment_review(
    db,
    *,
    learner_id: str,
    reviewer_id: str,
    lesson_id: str,
    rubric_version: str,
    knowledge_percent: int,
    competency_scores: dict[str, int],
    safety_gates: dict[str, bool],
    evidence_refs: list[str],
    decision: str,
    review_note: str | None = None,
):
    if not learner_id or not reviewer_id or learner_id == reviewer_id:
        raise ValueError("Valid distinct learner and reviewer IDs are required.")
    if not lesson_id or not rubric_version or decision not in {"APPROVED", "REJECTED", "REVIEW_REQUIRED"}:
        raise ValueError("Invalid assessment identifiers or decision.")
    assessment = PracticalAssessment(
        assessment_id=f"CP-PA-{uuid.uuid4().hex[:12].upper()}",
        learner_id=learner_id,
        reviewer_id=reviewer_id,
        lesson_id=lesson_id,
        rubric_version=rubric_version,
        knowledge_percent=knowledge_percent,
        competency_scores_json=json.dumps(competency_scores, sort_keys=True),
        safety_gates_json=json.dumps(safety_gates, sort_keys=True),
        evidence_refs_json=json.dumps(evidence_refs),
        decision=decision,
        review_note=review_note,
    )
    audit = AuditEvent(
        user_id=reviewer_id,
        action="PRACTICAL_ASSESSMENT_REVIEW",
        category="ACADEMY",
        resource_type="PRACTICAL_ASSESSMENT",
        resource_id=assessment.assessment_id,
        result=decision,
        reason=review_note,
    )
    db.add(assessment)
    db.add(audit)
    return assessment
