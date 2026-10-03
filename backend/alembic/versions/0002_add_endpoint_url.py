"""add endpoint_url to app_versions

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_versions",
        sa.Column("endpoint_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_versions", "endpoint_url")
