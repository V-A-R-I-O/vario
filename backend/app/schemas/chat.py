from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1)
    # Talk mode is a later slice — keep the field, default to chat.
    mode: str = "chat"


class SessionState(BaseModel):
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response_text: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    session: SessionState
