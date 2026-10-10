from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ConversationCreate(BaseModel):
    role_pack: str
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    role_pack: str
    title: Optional[str]
    last_message_preview: Optional[str] = None
    status: str
    created_at: datetime
    last_message_at: datetime

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]

class ConversationCreateResponse(BaseModel):
    id: str
    role_pack: str
    title: Optional[str]
    status: str
    created_at: datetime

class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    intent_name: Optional[str] = None
    confidence: Optional[float] = None
    entities: Optional[Dict[str, Any]] = None
    created_at: datetime

class MessageListResponse(BaseModel):
    conversation_id: str
    messages: List[MessageResponse]
