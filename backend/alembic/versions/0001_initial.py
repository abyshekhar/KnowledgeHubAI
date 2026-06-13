"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from backend.app.infrastructure.database.models import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    from backend.app.infrastructure.database.models import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)

