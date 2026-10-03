"""initial

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
    )

    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "dataset_rows",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("input", sa.Text, nullable=False),
        sa.Column("expected_output", sa.Text, nullable=True),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("tags", sa.String(255), nullable=True),
        sa.Column("metadata_json", postgresql.JSON, server_default="{}"),
    )

    op.create_table(
        "app_versions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("prompt_template", sa.Text, nullable=True),
        sa.Column("retriever_config", postgresql.JSON, server_default="{}"),
        sa.Column("git_note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scorers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scorer_type", sa.String(50), nullable=False),
        sa.Column("config_json", postgresql.JSON, server_default="{}"),
        sa.Column("prompt_template", sa.Text, nullable=True),
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("app_version_id", sa.Integer, sa.ForeignKey("app_versions.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "eval_run_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_id", sa.Integer, sa.ForeignKey("dataset_rows.id"), nullable=False),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("token_in", sa.Integer, nullable=True),
        sa.Column("token_out", sa.Integer, nullable=True),
        sa.Column("pass_fail", sa.Boolean, nullable=True),
        sa.Column("scorer_results_json", postgresql.JSON, server_default="{}"),
    )

    op.create_table(
        "trace_spans",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_item_id", sa.Integer, sa.ForeignKey("eval_run_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("span_name", sa.String(255), nullable=False),
        sa.Column("parent_id", sa.Integer, nullable=True),
        sa.Column("start_ms", sa.BigInteger, nullable=True),
        sa.Column("end_ms", sa.BigInteger, nullable=True),
        sa.Column("metadata_json", postgresql.JSON, server_default="{}"),
    )

    op.create_table(
        "aggregate_metrics",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scorer_id", sa.Integer, sa.ForeignKey("scorers.id"), nullable=True),
        sa.Column("avg_score", sa.Float, nullable=True),
        sa.Column("pass_rate", sa.Float, nullable=True),
        sa.Column("p95_latency", sa.Float, nullable=True),
        sa.Column("total_cost", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("aggregate_metrics")
    op.drop_table("trace_spans")
    op.drop_table("eval_run_items")
    op.drop_table("eval_runs")
    op.drop_table("scorers")
    op.drop_table("app_versions")
    op.drop_table("dataset_rows")
    op.drop_table("datasets")
    op.drop_table("users")
