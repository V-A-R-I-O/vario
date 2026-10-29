import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, JSON, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), unique=True, nullable=False)
    current_form = Column(String, nullable=True)
    current_step = Column(String, nullable=True)
    slots = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    # Set when the last bot reply asked for a secret; the next user message is redacted (ADR-006).
    sensitive_next_input = Column(Boolean, nullable=False, default=False, server_default=false())

    # Relationships
    conversation = relationship("Conversation", back_populates="session")
