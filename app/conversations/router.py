from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.conversations.schemas import (
    CoachingResult,
    MessageRead,
    SessionCreate,
    SessionRead,
    TextInput,
)
from app.conversations.service import coach_text, require_session
from app.core.dependencies import AI, DB, Catalog, Retrieval
from app.db.models import Message, StoreSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=201)
async def create_session(body: SessionCreate, db: DB):
    session = StoreSession(**body.model_dump())
    db.add(session)
    await db.commit()
    return session


@router.get("/{session_id}", response_model=SessionRead)
async def read_session(session_id: UUID, db: DB):
    return await require_session(db, session_id)


@router.get("/{session_id}/messages", response_model=list[MessageRead])
async def list_messages(
    session_id: UUID,
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    await require_session(db, session_id)
    return list(
        await db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at, Message.id)
            .offset(offset)
            .limit(limit)
        )
    )


@router.post("/{session_id}/messages", response_model=CoachingResult, status_code=201)
async def submit_text(
    session_id: UUID, body: TextInput, db: DB, ai: AI, catalog: Catalog, retriever: Retrieval
):
    return await coach_text(db, session_id, body.text, "text", ai, catalog, retriever)
