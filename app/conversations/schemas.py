from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.retrieval.schemas import RetrievalContext

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TranscriptText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)
]


class Stage(StrEnum):
    BEFORE_SHIFT = "before_shift"
    ASSESS = "assess"
    VALIDATE = "validate"
    TRANSLATE = "translate"
    RECOMMEND = "recommend"
    COMPLETE = "complete"
    CLOSE = "close"
    FOLLOW_THROUGH = "follow_through"
    REVIEW = "review"


class SessionCreate(BaseModel):
    associate_id: ShortText
    store_id: ShortText
    language: Annotated[str, StringConstraints(min_length=2, max_length=20)] = "en"


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    associate_id: str
    store_id: str
    language: str
    stage: Stage
    home_card: dict
    created_at: datetime


class TextInput(BaseModel):
    text: TranscriptText


class CoachReply(BaseModel):
    # The same schema constrains deterministic and live AI adapters.
    lines: list[
        Annotated[str, StringConstraints(min_length=1, max_length=300, pattern=r"^[^\r\n]+$")]
    ] = Field(min_length=1, max_length=3)
    buttons: list[
        Annotated[str, StringConstraints(min_length=1, max_length=20, pattern=r"^[^\r\n]+$")]
    ] = Field(max_length=3)
    reason: Annotated[str, StringConstraints(min_length=1, max_length=500)]


class CoachingResult(BaseModel):
    session_id: UUID
    input_message_id: UUID
    reply_message_id: UUID
    reply: CoachReply
    ai_provider: str
    dataset_status: str
    knowledge: RetrievalContext = Field(default_factory=RetrievalContext)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    source: str
    text: str
    details: dict
    created_at: datetime
