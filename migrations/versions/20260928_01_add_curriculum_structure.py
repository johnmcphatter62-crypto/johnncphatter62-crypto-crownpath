"""Add isolated CrownPath curriculum structure.

Revision ID: 20260928_01
Revises:
Create Date: 2026-09-28

Development-only migration. It is intentionally not wired into production
database initialization or deployment.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260928_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "curriculum_programs",
        sa.Column("program_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_curriculum_programs_slug"),
    )
    op.create_index("ix_curriculum_programs_slug", "curriculum_programs", ["slug"])
    op.create_index("ix_curriculum_programs_status", "curriculum_programs", ["status"])

    op.create_table(
        "curriculum_courses",
        sa.Column("course_id", sa.String(length=64), primary_key=True),
        sa.Column("program_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["curriculum_programs.program_id"]),
        sa.UniqueConstraint("program_id", "slug", name="uq_curriculum_course_slug"),
    )
    op.create_index("ix_curriculum_courses_program_id", "curriculum_courses", ["program_id"])

    op.create_table(
        "curriculum_units",
        sa.Column("unit_id", sa.String(length=64), primary_key=True),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["curriculum_courses.course_id"]),
    )
    op.create_index("ix_curriculum_units_course_id", "curriculum_units", ["course_id"])

    op.create_table(
        "curriculum_lessons",
        sa.Column("lesson_id", sa.String(length=100), primary_key=True),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("active_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["curriculum_units.unit_id"]),
    )
    op.create_index("ix_curriculum_lessons_unit_id", "curriculum_lessons", ["unit_id"])

    op.create_table(
        "curriculum_unit_lessons",
        sa.Column("assignment_id", sa.String(length=64), primary_key=True),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("lesson_id", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["curriculum_units.unit_id"]),
        sa.ForeignKeyConstraint(["lesson_id"], ["curriculum_lessons.lesson_id"]),
        sa.UniqueConstraint("unit_id", "lesson_id", name="uq_curriculum_unit_lesson"),
    )
    op.create_index("ix_curriculum_unit_lessons_unit_id", "curriculum_unit_lessons", ["unit_id"])
    op.create_index("ix_curriculum_unit_lessons_lesson_id", "curriculum_unit_lessons", ["lesson_id"])

    op.create_table(
        "curriculum_lesson_versions",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("lesson_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["curriculum_lessons.lesson_id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.user_id"]),
        sa.UniqueConstraint("lesson_id", "version", name="uq_curriculum_lesson_version"),
    )
    op.create_index("ix_curriculum_lesson_versions_lesson_id", "curriculum_lesson_versions", ["lesson_id"])

    op.create_table(
        "curriculum_activities",
        sa.Column("activity_id", sa.String(length=64), primary_key=True),
        sa.Column("lesson_id", sa.String(length=100), nullable=False),
        sa.Column("activity_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["curriculum_lessons.lesson_id"]),
    )
    op.create_index("ix_curriculum_activities_lesson_id", "curriculum_activities", ["lesson_id"])

    op.create_table(
        "curriculum_assessments",
        sa.Column("assessment_id", sa.String(length=64), primary_key=True),
        sa.Column("lesson_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("assessment_type", sa.String(length=40), nullable=False),
        sa.Column("mastery_threshold", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["curriculum_lessons.lesson_id"]),
    )
    op.create_index("ix_curriculum_assessments_lesson_id", "curriculum_assessments", ["lesson_id"])


def downgrade():
    op.drop_index("ix_curriculum_assessments_lesson_id", table_name="curriculum_assessments")
    op.drop_table("curriculum_assessments")
    op.drop_index("ix_curriculum_activities_lesson_id", table_name="curriculum_activities")
    op.drop_table("curriculum_activities")
    op.drop_index("ix_curriculum_lesson_versions_lesson_id", table_name="curriculum_lesson_versions")
    op.drop_table("curriculum_lesson_versions")
    op.drop_index("ix_curriculum_unit_lessons_lesson_id", table_name="curriculum_unit_lessons")
    op.drop_index("ix_curriculum_unit_lessons_unit_id", table_name="curriculum_unit_lessons")
    op.drop_table("curriculum_unit_lessons")
    op.drop_index("ix_curriculum_lessons_unit_id", table_name="curriculum_lessons")
    op.drop_table("curriculum_lessons")
    op.drop_index("ix_curriculum_units_course_id", table_name="curriculum_units")
    op.drop_table("curriculum_units")
    op.drop_index("ix_curriculum_courses_program_id", table_name="curriculum_courses")
    op.drop_table("curriculum_courses")
    op.drop_index("ix_curriculum_programs_status", table_name="curriculum_programs")
    op.drop_index("ix_curriculum_programs_slug", table_name="curriculum_programs")
    op.drop_table("curriculum_programs")
