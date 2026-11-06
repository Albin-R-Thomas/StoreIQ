from typing import Protocol

from pydantic import BaseModel, Field

from app.catalog.provider import CatalogContext
from app.conversations.schemas import CoachReply, Stage
from app.core.config import get_settings
from app.retrieval.schemas import RetrievalContext


class CoachingContext(BaseModel):
    stage: Stage
    language: str
    home_card: dict
    history: list[dict[str, str]]
    transcript: str
    catalog: CatalogContext
    knowledge: RetrievalContext = Field(default_factory=RetrievalContext)


class AIProvider(Protocol):
    name: str

    async def coach(self, context: CoachingContext) -> CoachReply: ...


class MockAIProvider:
    name = "mock"

    async def coach(self, context: CoachingContext) -> CoachReply:
        if context.knowledge.hits:
            hit = context.knowledge.hits[0]
            excerpt = " ".join(hit.text.split())
            if len(excerpt) > 220:
                excerpt = excerpt[:217] + "..."
            return CoachReply(
                lines=[
                    f"[Mock] Reference: {hit.title[:100]}",
                    f"Guidance: {excerpt}",
                    "Reason: matching guidance was retrieved; confirm details with the customer.",
                ],
                buttons=["Add home details", "Ask next question"],
                reason="Mock excerpt; verify product and commercial facts against the catalog.",
            )
        return CoachReply(
            lines=[
                "[Mock] Message text received; no knowledge match.",
                "Ask: How far from the TV will you usually sit?",
                "Reason: viewing distance helps understand the room before choosing a TV.",
            ],
            buttons=["Add home details", "Ask next question"],
            reason="Fixed TV scenario response for wiring the system; no product facts generated.",
        )


def get_ai_provider() -> AIProvider:
    if get_settings().ai_provider == "mock":
        return MockAIProvider()
    from app.ai.openai_provider import OpenAIProvider

    return OpenAIProvider()
