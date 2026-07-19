"""test generation tables

Revision ID: 0002_test_generation
Revises: 0001_initial
Create Date: 2026-07-19
"""

from __future__ import annotations

from alembic import op

revision = "0002_test_generation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_NEW_TABLES = [
    "test_gen_sessions",
    "test_clarifying_questions",
    "test_scenarios",
    "test_cases",
]


def upgrade() -> None:
    from backend.app.infrastructure.database.models import Base

    bind = op.get_bind()
    for table_name in _NEW_TABLES:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    from backend.app.infrastructure.database.models import Base

    bind = op.get_bind()
    for table_name in reversed(_NEW_TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
