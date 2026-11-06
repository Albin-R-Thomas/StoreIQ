from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmpty
    title: NonEmpty
    source: NonEmpty
    text: NonEmpty
    # Empty means global; store-specific documents must list their allowed store IDs.
    store_ids: list[NonEmpty] = Field(default_factory=list)
    is_mock: bool = True


class KnowledgeChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source: str
    text: str
    store_ids: list[str]
    is_mock: bool


class RetrievalHit(KnowledgeChunk):
    score: float


class RetrievalContext(BaseModel):
    provider: str = "disabled"
    status: Literal["disabled", "empty", "no_matches", "matched"] = "disabled"
    hits: list[RetrievalHit] = Field(default_factory=list)
