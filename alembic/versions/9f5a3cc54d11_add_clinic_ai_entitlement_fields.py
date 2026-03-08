"""add_clinic_ai_entitlement_fields

Revision ID: 9f5a3cc54d11
Revises: 58b785a471e0
Create Date: 2026-03-08 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f5a3cc54d11"
down_revision: Union[str, None] = "58b785a471e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("clinics", sa.Column("ai_policy_tier", sa.String(length=50), nullable=True))
    op.add_column("clinics", sa.Column("ai_guardrail_profile", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("clinics", "ai_guardrail_profile")
    op.drop_column("clinics", "ai_policy_tier")
    op.drop_column("clinics", "ai_enabled")
