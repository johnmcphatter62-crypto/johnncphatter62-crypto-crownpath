"""Evidence registry contract checks."""
from pathlib import Path

from crownpath.models import AssessmentEvidenceRecord


def test_registry_schema_fields():
    columns = AssessmentEvidenceRecord.__table__.c
    for name in ("evidence_id", "learner_id", "lesson_id", "evidence_type", "storage_reference", "consent_confirmed", "revoked"):
        assert name in columns


def test_registry_lookup_requires_learner_lesson_and_active_evidence():
    source = (Path(__file__).resolve().parents[1] / "crownpath" / "evidence_registry.py").read_text()
    assert "AssessmentEvidenceRecord.learner_id == learner_id" in source
    assert "AssessmentEvidenceRecord.lesson_id == lesson_id" in source
    assert "AssessmentEvidenceRecord.revoked.is_(False)" in source
    assert "not record.consent_confirmed" in source
