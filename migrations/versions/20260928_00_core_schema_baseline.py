"""Record CrownPath's pre-Alembic core schema.

Revision ID: 20260928_00
Revises:
Create Date: 2026-09-28

This is an intentionally empty baseline revision. CrownPath's existing core
tables predate Alembic migration tracking. Applying or rolling back this
revision performs no schema operations.
"""

revision = "20260928_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
