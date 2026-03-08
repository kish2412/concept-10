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
    op.add_column("encounters", sa.Column("ai_triage_summary", sa.Text(), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_focus_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_red_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_missing_information", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_orchestration", sa.String(length=120), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_model_provider", sa.String(length=80), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_model_name", sa.String(length=120), nullable=True))
    op.add_column("encounters", sa.Column("ai_triage_guardrail_profile", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("encounters", "ai_triage_guardrail_profile")
    op.drop_column("encounters", "ai_triage_model_name")
    op.drop_column("encounters", "ai_triage_model_provider")
    op.drop_column("encounters", "ai_triage_orchestration")
    op.drop_column("encounters", "ai_triage_generated_at")
    op.drop_column("encounters", "ai_triage_missing_information")
    op.drop_column("encounters", "ai_triage_red_flags")
    op.drop_column("encounters", "ai_triage_focus_points")
    op.drop_column("encounters", "ai_triage_summary")
