from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.conversations.schemas import CoachingResult, TranscriptText
from app.conversations.service import coach_text
from app.core.dependencies import AI, DB, Catalog, Retrieval
from app.recordings.transcription import mock_transcribe

router = APIRouter(prefix="/dev", tags=["development"])


class MockRecordingInput(BaseModel):
    session_id: UUID
    mock_recording_text: TranscriptText


@router.post("/mock-recordings", response_model=CoachingResult, status_code=201)
async def submit_mock_recording(
    body: MockRecordingInput, db: DB, ai: AI, catalog: Catalog, retriever: Retrieval
):
    return await coach_text(
        db,
        body.session_id,
        mock_transcribe(body.mock_recording_text),
        "mock_recording",
        ai,
        catalog,
        retriever,
    )
