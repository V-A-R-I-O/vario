from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1)
    # "chat" (text only) or "talk" (synthesize audio for the reply, slice-06).
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
    # Talk-mode fields (slice-06). Populated only for mode="talk"; null in chat
    # mode so the chat-mode contract (slice-05) is unchanged. When TTS is
    # unavailable, `tts_available` is False and `audio_base64` is null.
    audio_base64: Optional[str] = None
    audio_content_type: Optional[str] = None
    tts_available: Optional[bool] = None
