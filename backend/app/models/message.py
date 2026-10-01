import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False)
    sender = Column(String, nullable=False)
    content = Column(String, nullable=False)
    intent_name = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    entities = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(sender.in_(['user', 'bot']), name='chk_message_sender'),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
