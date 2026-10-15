from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action_type: str
    reference_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    role_pack: str
    total: int
    entries: List[AuditLogEntry] = Field(default_factory=list)


# --- Intents / Templates / Variants (slice-08) -----------------------------


class PhraseOut(BaseModel):
    id: str
    phrase_text: str


class VariantOut(BaseModel):
    id: str
    variant_text: str
    generated_at: Optional[datetime] = None


class TemplateOut(BaseModel):
    id: str
    template_key: str
    base_text: str
    allow_rephrasing: bool
    available_variables: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
    variants: List[VariantOut] = Field(default_factory=list)


class IntentOut(BaseModel):
    id: str
    name: str
    role_pack: str
    intent_type: str
    needs_retrain: bool
    updated_at: Optional[datetime] = None
    training_phrases: List[PhraseOut] = Field(default_factory=list)
    response_template: Optional[TemplateOut] = None


# Requests

class TemplateCreateIn(BaseModel):
    base_text: str = Field(min_length=1)
    allow_rephrasing: bool = True


class IntentCreate(BaseModel):
    name: str = Field(min_length=1)
    training_phrases: List[str] = Field(min_length=1)
    response_template: TemplateCreateIn


class PhraseEdit(BaseModel):
    add: List[str] = Field(default_factory=list)
    remove: List[str] = Field(default_factory=list)


class IntentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    training_phrases: Optional[PhraseEdit] = None


class TemplateUpdate(BaseModel):
    base_text: Optional[str] = Field(default=None, min_length=1)
    allow_rephrasing: Optional[bool] = None


class VariantUpdate(BaseModel):
    variant_text: str = Field(min_length=1)


class GeneratePhrasesRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=50)


# Response envelopes (become `data` in the gateway envelope)

class IntentListResponse(BaseModel):
    role_pack: str
    intents: List[IntentOut] = Field(default_factory=list)


class IntentResponse(BaseModel):
    intent: IntentOut


class IntentUpdateOut(BaseModel):
    id: str
    name: str
    needs_retrain: bool
    training_phrases: List[PhraseOut] = Field(default_factory=list)


class IntentUpdateResponse(BaseModel):
    intent: IntentUpdateOut


class IntentDeleteResponse(BaseModel):
    deleted_intent_id: str
    needs_retrain: bool = True


class TemplateListResponse(BaseModel):
    role_pack: str
    templates: List[TemplateOut] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    template: TemplateOut


class VariantResponse(BaseModel):
    variant: VariantOut


class VariantDeleteResponse(BaseModel):
    deleted_variant_id: str


class GeneratePhrasesResponse(BaseModel):
    intent_id: str
    generated_phrases: List[str] = Field(default_factory=list)


# --- Conversation Logs (slice-11, FR-19) -----------------------------------


class AdminConversationSummary(BaseModel):
    id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    title: Optional[str] = None
    message_count: int = 0
    last_intent: Optional[str] = None
    started_at: datetime
    last_message_at: Optional[datetime] = None


class AdminConversationListResponse(BaseModel):
    role_pack: str
    total: int
    conversations: List[AdminConversationSummary] = Field(default_factory=list)


class AdminMessageOut(BaseModel):
    id: str
    sender: str
    content: str
    intent_name: Optional[str] = None
    confidence: Optional[float] = None
    entities: Optional[Dict[str, Any]] = None
    created_at: datetime


class AdminTranscriptResponse(BaseModel):
    conversation_id: str
    role_pack: str
    user_name: Optional[str] = None
    messages: List[AdminMessageOut] = Field(default_factory=list)
