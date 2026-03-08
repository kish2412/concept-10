"""merge ai migration heads

Revision ID: b7c9d2e4f1a0
Revises: 1f3c7e9a2b11, 9f5a3cc54d11
Create Date: 2026-03-08 12:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "b7c9d2e4f1a0"
down_revision: Union[str, Sequence[str], None] = ("1f3c7e9a2b11", "9f5a3cc54d11")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge revision: schema changes already handled in parent branches.
    pass


def downgrade() -> None:
    # Unmerge revision marker.
    pass
