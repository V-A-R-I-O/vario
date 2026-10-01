import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class TrainingPhrase(Base):
    __tablename__ = "training_phrases"

    phrase_id = Column(String, primary_key=True, default=generate_uuid)
    intent_id = Column(String, ForeignKey("intents.intent_id"), nullable=False)
    phrase_text = Column(String, nullable=False)
    author_id = Column(String, ForeignKey("users.user_id"), nullable=True) # users (admin)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intent = relationship("Intent", back_populates="training_phrases")
    author = relationship("User", back_populates="training_phrases")
