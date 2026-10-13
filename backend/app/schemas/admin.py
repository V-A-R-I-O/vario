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
