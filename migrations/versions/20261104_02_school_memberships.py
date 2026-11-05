"""Stage school membership schema for isolated CrownPath development.

Revision ID: 20261104_02
Revises: 20260928_01

Not wired into application startup or production deployment. No school
memberships are automatically assigned and no device access is enabled.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261104_02"
down_revision = "20260928_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "schools",
        sa.Column("school_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "school_memberships",
        sa.Column("membership_id", sa.String(length=64), primary_key=True),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.user_id"]),
        sa.UniqueConstraint("school_id", "user_id", name="uq_school_membership_user"),
    )
    op.create_index("ix_school_memberships_user_id", "school_memberships", ["user_id"])
    op.create_index("ix_school_memberships_school_id", "school_memberships", ["school_id"])


def downgrade():
    op.drop_index("ix_school_memberships_school_id", table_name="school_memberships")
    op.drop_index("ix_school_memberships_user_id", table_name="school_memberships")
    op.drop_table("school_memberships")
    op.drop_table("schools")
