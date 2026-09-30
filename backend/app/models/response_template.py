import uuid
from sqlalchemy import Column, String, Boolean, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from app.database import Base
from .user import generate_uuid

class ResponseTemplate(Base):
    __tablename__ = "response_templates"

    template_id = Column(String, primary_key=True, default=generate_uuid)
    role_pack = Column(String, nullable=False)
    template_key = Column(String, nullable=False, unique=True)
    base_text = Column(String, nullable=False)
    allow_rephrasing = Column(Boolean, default=True)
    available_variables = Column(JSON().with_variant(ARRAY(String), 'postgresql'), default=list)

    __table_args__ = (
        CheckConstraint(role_pack.in_(['hr', 'it', 'admissions']), name='chk_response_template_role_pack'),
    )

    # Relationships
    variants = relationship("ResponseVariant", back_populates="template", cascade="all, delete-orphan")
