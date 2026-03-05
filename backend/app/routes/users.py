"""User and Conversation management routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import User, Conversation, Message, get_session_factory

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = ""
    is_anonymous: bool = True


class UpdatePreferencesRequest(BaseModel):
    preferences: dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: Optional[str]
    name: str
    is_anonymous: bool
    preferences: dict
    created_at: str
    last_active: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    summary: str
    message_count: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    extra_data: dict
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    summary: str
    messages: list[MessageResponse]
    created_at: str
    updated_at: str


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Research"


class AddMessageRequest(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    extra_data: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------


@router.post("/users", response_model=UserResponse)
async def create_user(request: CreateUserRequest):
    """Create a new user (anonymous or authenticated)."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            name=request.name or "Anonymous",
            is_anonymous=1 if request.is_anonymous else 0,
            preferences_json="{}",
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_anonymous=bool(user.is_anonymous),
            preferences=user.preferences,
            created_at=user.created_at.isoformat(),
            last_active=user.last_active.isoformat(),
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user details by ID."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_anonymous=bool(user.is_anonymous),
            preferences=user.preferences,
            created_at=user.created_at.isoformat(),
            last_active=user.last_active.isoformat(),
        )


@router.put("/users/{user_id}/preferences")
async def update_preferences(user_id: str, request: UpdatePreferencesRequest):
    """Update user preferences."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Merge with existing preferences
        current_prefs = user.preferences
        current_prefs.update(request.preferences)
        user.preferences = current_prefs
        user.last_active = datetime.utcnow()

        await session.commit()
        await session.refresh(user)

        return {
            "id": user.id,
            "preferences": user.preferences,
            "updated_at": user.last_active.isoformat(),
        }


# ---------------------------------------------------------------------------
# Conversation endpoints
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}/conversations", response_model=list[ConversationSummary])
async def list_conversations(user_id: str, limit: int = 50):
    """List all conversations for a user."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        conversations = result.scalars().all()

        summaries = []
        for conv in conversations:
            from sqlalchemy import func, select as sel
            msg_count_result = await session.execute(
                sel(func.count(Message.id)).where(Message.conversation_id == conv.id)
            )
            msg_count = msg_count_result.scalar() or 0

            summaries.append(
                ConversationSummary(
                    id=conv.id,
                    title=conv.title,
                    summary=conv.summary,
                    message_count=msg_count,
                    created_at=conv.created_at.isoformat(),
                    updated_at=conv.updated_at.isoformat(),
                )
            )

        return summaries


@router.post("/users/{user_id}/conversations", response_model=ConversationDetail)
async def create_conversation(user_id: str, request: CreateConversationRequest):
    """Create a new conversation for a user."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select

        # Verify user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=request.title or "New Research",
            summary="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            summary=conversation.summary,
            messages=[],
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """Get conversation details with all messages."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get all messages
        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            summary=conversation.summary,
            messages=[
                MessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    extra_data=msg.extra_data,
                    created_at=msg.created_at.isoformat(),
                )
                for msg in messages
            ],
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
        )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(conversation_id: str, request: AddMessageRequest):
    """Add a message to a conversation."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select

        # Verify conversation exists
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            extra_data_json="{}",
            created_at=datetime.utcnow(),
        )
        message.extra_data = request.extra_data

        session.add(message)

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(message)

        return MessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            extra_data=message.extra_data,
            created_at=message.created_at.isoformat(),
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select, delete

        # Verify conversation exists
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Delete messages first (cascade should handle this, but explicit is safer)
        await session.execute(
            delete(Message).where(Message.conversation_id == conversation_id)
        )

        # Delete conversation
        await session.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )

        await session.commit()

        return {"id": conversation_id, "deleted": True}


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, title: str):
    """Update conversation title."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation.title = title
        conversation.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(conversation)

        return {
            "id": conversation.id,
            "title": conversation.title,
            "updated_at": conversation.updated_at.isoformat(),
        }
