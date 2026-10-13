"""Add role_pack to audit_log (slice-07 admin-shell)

Admin audit-log reads are scoped to the admin's own role pack, so each entry
records which pack (hr/it/admissions) the event belongs to.

Revision ID: b1c2d3e4f5a6
Revises: 7a00a2c7bd94
Create Date: 2026-10-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "7a00a2c7bd94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("audit_log", sa.Column("role_pack", sa.String(), nullable=True))
    op.create_index("ix_audit_log_role_pack", "audit_log", ["role_pack"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_audit_log_role_pack", table_name="audit_log")
    op.drop_column("audit_log", "role_pack")
