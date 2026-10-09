"""Schema contract checks before a versioned assessment migration is authored."""
from sqlalchemy import ForeignKeyConstraint, Index

from crownpath.models import PracticalAssessment


def test_assessment_table_has_expected_primary_key_and_user_foreign_keys():
    table = PracticalAssessment.__table__
    assert table.name == "practical_assessments"
    assert {col.name for col in table.primary_key.columns} == {"assessment_id"}
    foreign_keys = {
        (fk.parent.name, fk.target_fullname)
        for fk in table.foreign_keys
    }
    assert ("learner_id", "users.user_id") in foreign_keys
    assert ("reviewer_id", "users.user_id") in foreign_keys


def test_assessment_columns_are_non_nullable_where_required():
    table = PracticalAssessment.__table__
    for name in (
        "learner_id", "reviewer_id", "lesson_id", "rubric_version",
        "knowledge_percent", "competency_scores_json", "safety_gates_json",
        "evidence_refs_json", "decision", "reviewed_at",
    ):
        assert table.c[name].nullable is False, name


def test_assessment_lookup_columns_have_indexes():
    table = PracticalAssessment.__table__
    indexed_columns = {
        column.name
        for index in table.indexes
        for column in index.columns
    }
    assert {"learner_id", "reviewer_id", "lesson_id"} <= indexed_columns
