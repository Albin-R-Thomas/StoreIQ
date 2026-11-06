from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, CoachingContext
from app.catalog.provider import CatalogProvider
from app.conversations.schemas import CoachingResult
from app.db.models import Message, StoreSession
from app.retrieval.provider import Retriever


async def require_session(db: AsyncSession, session_id: UUID) -> StoreSession:
    session = await db.get(StoreSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def coach_text(
    db: AsyncSession,
    session_id: UUID,
    text: str,
    source: str,
    ai: AIProvider,
    catalog: CatalogProvider,
    retriever: Retriever,
    input_details: dict | None = None,
) -> CoachingResult:
    session = await require_session(db, session_id)
    recent = list(
        await db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(20)
        )
    )
    dataset = await catalog.context_for(session.store_id)
    knowledge = await retriever.retrieve(text, session.store_id)
    reply = await ai.coach(
        CoachingContext(
            stage=session.stage,
            language=session.language,
            home_card=session.home_card,
            history=[{"role": m.role, "text": m.text} for m in reversed(recent)],
            transcript=text,
            catalog=dataset,
            knowledge=knowledge,
        )
    )
    incoming = Message(
        session_id=session_id,
        role="associate",
        source=source,
        text=text,
        details=input_details or {},
    )
    outgoing = Message(
        session_id=session_id,
        role="assistant",
        source=ai.name,
        text="\n".join(reply.lines),
        details={
            "reply": reply.model_dump(),
            "dataset_status": dataset.status,
            "knowledge": knowledge.model_dump(),
        },
    )
    db.add_all([incoming, outgoing])
    await db.commit()
    return CoachingResult(
        session_id=session_id,
        input_message_id=incoming.id,
        reply_message_id=outgoing.id,
        reply=reply,
        ai_provider=ai.name,
        dataset_status=dataset.status,
        knowledge=knowledge,
    )
