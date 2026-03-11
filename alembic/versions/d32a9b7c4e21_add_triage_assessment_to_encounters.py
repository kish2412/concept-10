"""add triage assessment to encounters

Revision ID: d32a9b7c4e21
Revises: b7c9d2e4f1a0
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d32a9b7c4e21"
down_revision: Union[str, None] = "b7c9d2e4f1a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "encounters",
        sa.Column("triage_assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("encounters", "triage_assessment")
