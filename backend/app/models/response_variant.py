import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class ResponseVariant(Base):
    __tablename__ = "response_variants"

    variant_id = Column(String, primary_key=True, default=generate_uuid)
    template_id = Column(String, ForeignKey("response_templates.template_id"), nullable=False)
    variant_text = Column(String, nullable=False)
    # Ordering within a template. Position 0 is the original base_text variant,
    # which cannot be deleted (slice-08). Generated variants follow at 1, 2, ….
    position = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("ResponseTemplate", back_populates="variants")
