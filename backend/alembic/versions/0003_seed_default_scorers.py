"""seed default scorers

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-03 00:00:00

"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_DEFAULT_SCORERS = [
    ("Exact Match",             "exact_match",        '{"threshold": 1.0}'),
    ("Keyword Coverage",        "keyword_coverage",   '{"threshold": 0.7}'),
    ("JSON Validity",           "json_validity",      '{"threshold": 1.0}'),
    ("LLM Correctness Judge",   "llm_judge",          '{"model": "gpt-4o-mini", "threshold": 0.6}'),
    ("RAGAS Faithfulness",      "ragas_faithfulness", '{"model": "gpt-4o-mini", "threshold": 0.7}'),
]


def upgrade() -> None:
    for name, scorer_type, config in _DEFAULT_SCORERS:
        op.execute(
            f"INSERT INTO scorers (name, scorer_type, config_json) "
            f"VALUES ('{name}', '{scorer_type}', '{config}'::jsonb)"
        )


def downgrade() -> None:
    names = ", ".join(f"'{n}'" for n, _, _ in _DEFAULT_SCORERS)
    op.execute(f"DELETE FROM scorers WHERE name IN ({names})")
