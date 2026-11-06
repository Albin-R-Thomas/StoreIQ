from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints

from app.conversations.schemas import CoachingResult
from app.conversations.service import coach_text
from app.core.dependencies import AI, DB, Catalog, Retrieval
from app.meta.text import MetaTextMessage, extract_text, make_mock_text_message

router = APIRouter(prefix="/dev", tags=["development"])
PhoneNumber = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{6,14}$")]


class MockWhatsAppInput(BaseModel):
    session_id: UUID
    mock_whatsapp_text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)
    ]
    sender: PhoneNumber = "15550100001"


class MockWhatsAppOutbound(BaseModel):
    mode: Literal["mock"] = "mock"
    message_id: str
    recipient: str
    text: str


class MockWhatsAppResult(BaseModel):
    inbound: MetaTextMessage
    coaching: CoachingResult
    outbound: MockWhatsAppOutbound


@router.post("/mock-whatsapp-text", response_model=MockWhatsAppResult, status_code=201)
async def mock_whatsapp_text(
    body: MockWhatsAppInput, db: DB, ai: AI, catalog: Catalog, retriever: Retrieval
):
    inbound = make_mock_text_message(body.sender, body.mock_whatsapp_text)
    result = await coach_text(
        db,
        body.session_id,
        extract_text(inbound),
        "mock_whatsapp_text",
        ai,
        catalog,
        retriever,
        input_details={"whatsapp": inbound.model_dump(by_alias=True), "transport": "mock"},
    )
    # Deliberately no Meta client dependency: this endpoint cannot send to WhatsApp.
    outbound = MockWhatsAppOutbound(
        message_id=f"mock-{uuid4()}", recipient=body.sender, text="\n".join(result.reply.lines)
    )
    return MockWhatsAppResult(inbound=inbound, coaching=result, outbound=outbound)
