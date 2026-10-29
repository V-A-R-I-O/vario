"""Add messages.card and sessions.sensitive_next_input (slice-32 rasa-contract-v2)

`messages.card` stores the UI card for each bot turn so cards survive a reload.
`sessions.sensitive_next_input` marks that the next user message is a secret
and must be redacted before it is stored. See ADR-006.

Revision ID: e4f5a6b7c8d9
Revises: c2d3e4f5a6b7
Create Date: 2026-10-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "messages",
        sa.Column("card", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("sensitive_next_input", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sessions", "sensitive_next_input")
    op.drop_column("messages", "card")
