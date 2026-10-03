"""add retrieved_chunks_json to eval_run_items

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-05 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_run_items",
        sa.Column(
            "retrieved_chunks_json",
            postgresql.JSON,
            nullable=True,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("eval_run_items", "retrieved_chunks_json")
