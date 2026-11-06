"""Authenticated local simulator; never exposed as an unauthenticated webhook."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.messaging import service
from app.messaging.adapters import get_adapter
from app.messaging.contracts import DeliveryUpdate, IncomingMessage
from app.web import domain
from app.web.api import User, rate_limit
from app.web.store import read_all, transaction

router = APIRouter(prefix="/api/messaging/mock", tags=["mock-whatsapp"])


def mock_adapter():
    if not get_settings().enable_dev_routes or os.getenv("DEMO_MODE", "true").lower() != "true":
        raise HTTPException(404, "Mock messaging is disabled")
    adapter = get_adapter()
    if adapter.name != "mock":
        raise HTTPException(404, "Mock messaging is disabled for this provider")
    return adapter


Adapter = Annotated[object, Depends(mock_adapter)]


@router.post("/events")
async def receive(body: IncomingMessage, user: User, adapter: Adapter):
    rate_limit("messaging:" + user["id"], 60)
    event = adapter.decode(body.model_dump_json().encode(), {})
    inbox = await service.receive(event, user, adapter)
    with transaction() as db:
        messages = [
            service.owned_record(db, "messaging_outbox", key, user) for key in inbox["outbox_ids"]
        ]
    return {"event": inbox, "messages": messages, "simulated": True}


@router.get("/outbox")
def outbox(user: User, adapter: Adapter, customer_id: str | None = None):
    with transaction() as db:
        if customer_id:
            domain.owned(db, "customers", customer_id, user)
        return {
            "simulated": True,
            "messages": [
                item
                for item in read_all(db, "messaging_outbox")
                if item["owner"] == user["id"]
                and item["provider"] == adapter.name
                and (not customer_id or item["message"]["customer_id"] == customer_id)
            ],
        }


@router.post("/outbox/{message_id}/retry")
async def retry(message_id: str, user: User, adapter: Adapter):
    rate_limit("messaging:" + user["id"], 60)
    return await service.dispatch(message_id, user, adapter)


@router.post("/outbox/{message_id}/delivery")
def delivery(message_id: str, body: DeliveryUpdate, user: User, adapter: Adapter):
    return service.delivery(message_id, body, user, adapter.name)
