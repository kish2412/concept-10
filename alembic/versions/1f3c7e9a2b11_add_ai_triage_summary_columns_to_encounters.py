"""add_ai_triage_summary_columns_to_encounters

Revision ID: 1f3c7e9a2b11
Revises: 58b785a471e0
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1f3c7e9a2b11"
down_revision: Union[str, None] = "58b785a471e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # AI-related columns removed. No longer added to encounters table.


def downgrade() -> None:
    # AI-related columns removed. No longer dropped from encounters table.
    op.drop_column("encounters", "ai_triage_focus_points")
    op.drop_column("encounters", "ai_triage_summary")
