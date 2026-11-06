from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.conversations.schemas import ShortText, TranscriptText
from app.core.dependencies import Retrieval
from app.retrieval.schemas import RetrievalContext

router = APIRouter(prefix="/dev/retrieval", tags=["development"])


class SearchInput(BaseModel):
    query: TranscriptText
    store_id: ShortText
    top_k: Annotated[int, Field(ge=1, le=10)] | None = None


@router.post("/search", response_model=RetrievalContext)
async def search(body: SearchInput, retriever: Retrieval):
    return await retriever.retrieve(body.query, body.store_id, body.top_k)
