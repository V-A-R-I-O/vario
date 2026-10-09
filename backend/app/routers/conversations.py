from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    ConversationCreateResponse,
    MessageResponse,
    MessageListResponse
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    role_pack: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    user_id = request.state.user_id
    
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    if role_pack:
        stmt = stmt.where(Conversation.role_pack == role_pack)
    if status:
        stmt = stmt.where(Conversation.status == status)
        
    stmt = stmt.order_by(desc(Conversation.last_message_at))
    
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    resp_list = []
    for conv in conversations:
        # Fetch last message for preview
        msg_stmt = select(Message).where(Message.conversation_id == conv.conversation_id).order_by(desc(Message.created_at)).limit(1)
        msg_result = await db.execute(msg_stmt)
        last_msg = msg_result.scalars().first()
        
        resp_list.append(
            ConversationResponse(
                id=conv.conversation_id,
                role_pack=conv.role_pack,
                title=conv.title,
                last_message_preview=last_msg.content if last_msg else None,
                status=conv.status,
                created_at=conv.created_at,
                last_message_at=conv.last_message_at
            )
        )
        
    return ConversationListResponse(conversations=resp_list)

@router.post("", response_model=ConversationCreateResponse, status_code=201)
async def create_conversation(
    request: Request,
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    user_id = request.state.user_id
    
    if payload.role_pack not in ["hr", "it", "admissions"]:
        raise HTTPException(status_code=422, detail="Invalid role_pack value")
        
    title = payload.title or f"New {payload.role_pack.upper()} conversation"
    
    conv = Conversation(
        user_id=user_id,
        role_pack=payload.role_pack,
        title=title
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    
    return ConversationCreateResponse(
        id=conv.conversation_id,
        role_pack=conv.role_pack,
        title=conv.title,
        status=conv.status,
        created_at=conv.created_at
    )

@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    request: Request,
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    user_id = request.state.user_id
    
    # Check ownership
    conv_result = await db.execute(select(Conversation).where(Conversation.conversation_id == conversation_id))
    conv = conv_result.scalars().first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Conversation does not belong to this user")
        
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    
    if before:
        # Find the cursor message
        cursor_result = await db.execute(select(Message).where(Message.message_id == before))
        cursor_msg = cursor_result.scalars().first()
        if cursor_msg:
            stmt = stmt.where(Message.created_at < cursor_msg.created_at)
            
    stmt = stmt.order_by(desc(Message.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    resp_msgs = [
        MessageResponse(
            id=m.message_id,
            sender=m.sender,
            content=m.content,
            intent_name=m.intent_name,
            confidence=m.confidence,
            entities=m.entities,
            created_at=m.created_at
        ) for m in messages
    ]
    
    # The API contract returns them sorted most recent first? Wait, chat history is usually older first.
    # The API contract just lists them. Standard for history is returning older first, 
    # but the cursor `before` and `desc` implies we fetch newest `limit` messages before the cursor.
    # We should reverse the list so it's chronologically ordered (oldest to newest) for frontend rendering.
    resp_msgs.reverse()
    
    return MessageListResponse(
        conversation_id=conversation_id,
        messages=resp_msgs
    )
