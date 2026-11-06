from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from app.conversations.schemas import TranscriptText
from app.meta.schemas import MetaMessage


class MetaTextBody(BaseModel):
    body: TranscriptText


class MetaTextMessage(MetaMessage):
    type: Literal["text"] = "text"
    text: MetaTextBody


def make_mock_text_message(sender: str, text: str) -> MetaTextMessage:
    return MetaTextMessage.model_validate(
        {"id": f"wamid.MOCK_{uuid4()}", "from": sender, "type": "text", "text": {"body": text}}
    )


def extract_text(message: MetaMessage) -> str:
    """Shared text normalization seam for mocks and a future inbox processor."""
    normalized = MetaTextMessage.model_validate(message.model_dump(by_alias=True))
    return normalized.text.body
