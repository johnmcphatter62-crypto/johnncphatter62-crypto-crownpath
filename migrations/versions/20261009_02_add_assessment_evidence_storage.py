"""Add assessment and evidence metadata tables (development migration).

Revision ID: 20261009_02
Revises: 20260928_01

Requires existing core users table and curriculum revision. Do not run on a
database with schema drift or tables created by create_all without reconciliation.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261009_02"
down_revision = "20260928_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "practical_assessments",
        sa.Column("assessment_id", sa.String(64), primary_key=True),
        sa.Column("learner_id", sa.String(64), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("reviewer_id", sa.String(64), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("lesson_id", sa.String(100), nullable=False),
        sa.Column("rubric_version", sa.String(40), nullable=False),
        sa.Column("knowledge_percent", sa.Integer(), nullable=False),
        sa.Column("competency_scores_json", sa.Text(), nullable=False),
        sa.Column("safety_gates_json", sa.Text(), nullable=False),
        sa.Column("evidence_refs_json", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("knowledge_percent >= 0 AND knowledge_percent <= 100", name="ck_practical_assessment_knowledge_range"),
        sa.CheckConstraint("decision IN ('APPROVED', 'REJECTED', 'REVIEW_REQUIRED')", name="ck_practical_assessment_decision"),
        sa.CheckConstraint("learner_id <> reviewer_id", name="ck_practical_assessment_distinct_reviewer"),
    )
    for field in ("learner_id", "reviewer_id", "lesson_id"):
        op.create_index(f"ix_practical_assessments_{field}", "practical_assessments", [field])

    op.create_table(
        "assessment_evidence_records",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("learner_id", sa.String(64), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("lesson_id", sa.String(100), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("storage_reference", sa.String(255), nullable=False, unique=True),
        sa.Column("consent_confirmed", sa.Boolean(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for field in ("learner_id", "lesson_id"):
        op.create_index(f"ix_assessment_evidence_records_{field}", "assessment_evidence_records", [field])

    op.create_table(
        "evidence_storage_objects",
        sa.Column("storage_reference", sa.String(255), primary_key=True),
        sa.Column("learner_id", sa.String(64), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("lesson_id", sa.String(100), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("upload_complete", sa.Boolean(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_storage_objects_learner_id", "evidence_storage_objects", ["learner_id"])


def downgrade():
    op.drop_index("ix_evidence_storage_objects_learner_id", table_name="evidence_storage_objects")
    op.drop_table("evidence_storage_objects")
    for field in ("lesson_id", "learner_id"):
        op.drop_index(f"ix_assessment_evidence_records_{field}", table_name="assessment_evidence_records")
    op.drop_table("assessment_evidence_records")
    for field in ("lesson_id", "reviewer_id", "learner_id"):
        op.drop_index(f"ix_practical_assessments_{field}", table_name="practical_assessments")
    op.drop_table("practical_assessments")
