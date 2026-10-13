import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True) # actor
    # Role pack this event belongs to (hr/it/admissions). Admin audit-log reads
    # are scoped to the admin's own role pack (slice-07).
    role_pack = Column(String, nullable=True, index=True)
    action_type = Column(String, nullable=False)
    reference_id = Column(String, nullable=True)
    details = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    actor = relationship("User", back_populates="audit_logs")
