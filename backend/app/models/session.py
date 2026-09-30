import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
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

    # Relationships
    conversation = relationship("Conversation", back_populates="session")
