"""Stage explicit school-scoped Owner grants; no grants are created.

Revision ID: 20261104_03
Revises: 20261104_02

Development branch only; not wired to HTTP, device access or production.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261104_03"
down_revision = "20261104_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "school_owner_authorizations",
        sa.Column("authorization_id", sa.String(length=64), primary_key=True),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.user_id"]),
        sa.UniqueConstraint("school_id", "owner_user_id", name="uq_school_owner_authorization"),
    )
    op.create_index(
        "ix_school_owner_authorizations_owner",
        "school_owner_authorizations",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_school_owner_authorizations_school",
        "school_owner_authorizations",
        ["school_id"],
    )


def downgrade():
    op.drop_index(
        "ix_school_owner_authorizations_school",
        table_name="school_owner_authorizations",
    )
    op.drop_index(
        "ix_school_owner_authorizations_owner",
        table_name="school_owner_authorizations",
    )
    op.drop_table("school_owner_authorizations")
