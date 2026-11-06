from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.voice import audio, service
from app.voice.contracts import Confirm, Language, Prepare, Revision
from app.web import domain
from app.web.api import User, rate_limit
from app.web.store import transaction

router = APIRouter(prefix="/api", tags=["voice"])


@router.post(
    "/customers/{customer_id}/voice",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                kind: {"schema": {"type": "string", "format": "binary"}} for kind in audio.FORMATS
            },
        }
    },
)
async def upload(
    customer_id: str,
    request: Request,
    user: User,
    event_id: Annotated[str, Query(min_length=1, max_length=100)],
    version: Annotated[int, Query(ge=1)],
    source_language: Literal["en", "hi", "mr", "auto"] = "auto",
    target_language: Language | None = None,
):
    """Raw audio body (not multipart). No URL fetching or caller-supplied local paths."""
    rate_limit("voice:" + user["id"], 10)
    with transaction() as db:
        domain.owned(db, "customers", customer_id, user)
    media_type = request.headers.get("content-type", "").split(";")[0].lower()
    if media_type not in audio.FORMATS:
        raise HTTPException(415, "Unsupported audio content type")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > audio.MAX_BYTES:
            raise HTTPException(413, "Audio exceeds the 10 MiB limit")
        content.extend(chunk)
    return await service.upload(
        customer_id,
        version,
        event_id,
        bytes(content),
        media_type,
        None if source_language == "auto" else source_language,
        target_language,
        user,
    )


@router.get("/customers/{customer_id}/voice")
def drafts(customer_id: str, user: User):
    return service.drafts(customer_id, user)


@router.post("/voice/{voice_id}/prepare")
async def prepare(voice_id: str, body: Prepare, user: User):
    rate_limit("voice:" + user["id"], 10)
    return await service.prepare(voice_id, body, user)


@router.post("/voice/{voice_id}/confirm")
def confirm(voice_id: str, body: Confirm, user: User):
    return service.confirm(voice_id, body, user)


@router.post("/voice/{voice_id}/discard")
def discard(voice_id: str, body: Revision, user: User):
    return service.discard(voice_id, body.revision, user)
