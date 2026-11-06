import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, StringConstraints, ValidationError
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.dependencies import DB
from app.core.errors import IntegrationNotConfigured
from app.db.models import WebhookInbox
from app.meta.client import MetaClient, SendResult, get_meta_client
from app.meta.schemas import MetaWebhook, WebhookReceipt

router = APIRouter(prefix="/meta", tags=["meta"])
dev_router = APIRouter(prefix="/dev/meta", tags=["development"])


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    mode: Annotated[str, Query(alias="hub.mode")],
    token: Annotated[str, Query(alias="hub.verify_token")],
    challenge: Annotated[str, Query(alias="hub.challenge")],
):
    expected = get_settings().meta_verify_token.get_secret_value()
    if not expected:
        raise IntegrationNotConfigured("Set META_VERIFY_TOKEN before verifying a webhook.")
    if mode != "subscribe" or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return challenge


@router.post("/webhook", response_model=WebhookReceipt)
async def receive_webhook(
    request: Request,
    db: DB,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
):
    secret = get_settings().meta_app_secret.get_secret_value()
    if not secret:
        raise IntegrationNotConfigured("Set META_APP_SECRET before receiving webhooks.")
    raw = await request.body()
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if signature is None or not hmac.compare_digest(signature.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid Meta signature")
    try:
        event = MetaWebhook.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid Meta webhook payload") from exc
    accepted = duplicates = 0
    if event.object == "whatsapp_business_account":
        for entry in event.entry:
            for change in entry.changes:
                if change.field != "messages":
                    continue
                if change.value.messages and change.value.metadata is None:
                    raise HTTPException(status_code=422, detail="Message metadata missing")
                for message in change.value.messages:
                    statement = (
                        insert(WebhookInbox)
                        .values(
                            phone_number_id=change.value.metadata.phone_number_id,
                            message_id=message.id,
                            sender=message.from_,
                            message_type=message.type,
                            payload=message.model_dump(by_alias=True),
                        )
                        .on_conflict_do_nothing(constraint="uq_meta_message")
                        .returning(WebhookInbox.id)
                    )
                    inserted = (await db.execute(statement)).scalar_one_or_none()
                    if inserted is None:
                        duplicates += 1
                    else:
                        accepted += 1
    await db.commit()
    return WebhookReceipt(accepted=accepted, duplicates=duplicates)


class SendTextInput(BaseModel):
    recipient: Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{6,14}$")]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]


@dev_router.post("/send-text", response_model=SendResult)
async def send_text(body: SendTextInput, client: Annotated[MetaClient, Depends(get_meta_client)]):
    return await client.send_text(body.recipient, body.text)
