"""add scorer_ids to eval_runs

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-04 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_runs",
        sa.Column(
            "scorer_ids",
            postgresql.JSON,
            nullable=True,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("eval_runs", "scorer_ids")
