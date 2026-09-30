import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class Intent(Base):
    __tablename__ = "intents"

    intent_id = Column(String, primary_key=True, default=generate_uuid)
    role_pack = Column(String, nullable=False)
    name = Column(String, nullable=False, unique=True)
    intent_type = Column(String, nullable=False)
    needs_retrain = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(role_pack.in_(['hr', 'it', 'admissions']), name='chk_intent_role_pack'),
        CheckConstraint(intent_type.in_(['dynamic_workflow', 'static_faq']), name='chk_intent_type'),
    )

    # Relationships
    training_phrases = relationship("TrainingPhrase", back_populates="intent", cascade="all, delete-orphan")
