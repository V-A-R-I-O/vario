"""Persist asynchronous retraining job status.

Revision ID: d3f4a5b6c7d8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retraining_jobs",
        sa.Column("job_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("role_pack", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("intent_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("role_pack IN ('hr', 'it', 'admissions')", name="chk_retraining_job_role_pack"),
        sa.CheckConstraint("state IN ('pending', 'training', 'complete', 'failed')", name="chk_retraining_job_state"),
    )
    op.create_index("ix_retraining_jobs_role_pack", "retraining_jobs", ["role_pack"])
    op.create_index("ix_retraining_jobs_state", "retraining_jobs", ["state"])


def downgrade() -> None:
    op.drop_index("ix_retraining_jobs_state", table_name="retraining_jobs")
    op.drop_index("ix_retraining_jobs_role_pack", table_name="retraining_jobs")
    op.drop_table("retraining_jobs")
