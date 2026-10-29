"""Durable status for asynchronous role-pack retraining jobs."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, CheckConstraint, Integer, Index
from app.database import Base
from .user import generate_uuid


class RetrainingJob(Base):
    __tablename__ = "retraining_jobs"

    job_id = Column(String, primary_key=True, default=generate_uuid)
    role_pack = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=False)
    state = Column(String, nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    intent_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(role_pack.in_(["hr", "it", "admissions"]), name="chk_retraining_job_role_pack"),
        CheckConstraint(state.in_(["pending", "training", "complete", "failed"]), name="chk_retraining_job_state"),
        Index(
            "uq_retraining_jobs_one_active_per_pack",
            "role_pack",
            unique=True,
            sqlite_where=state.in_(["pending", "training"]),
            postgresql_where=state.in_(["pending", "training"]),
        ),
    )
