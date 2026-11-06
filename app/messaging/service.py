"""Durable inbox/outbox; business calls do not depend on Meta or Twilio."""

import asyncio
import hashlib
import json
import time

from fastapi import HTTPException
from pydantic import ValidationError

from app.messaging.contracts import (
    DeliveryUpdate,
    IncomingMessage,
    MessagingAdapter,
    OutgoingMessage,
    ProviderUnavailable,
    SendReceipt,
)
from app.web import domain, flow
from app.web.actions import validate
from app.web.store import audit, get, now, put, read_all, transaction, uid


def event_key(provider, owner, event_id):
    return hashlib.sha256(json.dumps([provider, owner, event_id]).encode()).hexdigest()


def owned_record(db, kind, key, user):
    record = get(db, kind, key)
    if not record:
        raise HTTPException(404, "Message not found")
    if record["owner"] != user["id"]:
        raise HTTPException(403, "Message belongs to another associate")
    return record


def enqueue(db, inbox, customer):
    prompt = flow.build(db, customer)
    # Include the actual answer, not just the generic follow-up prompt.
    answers = [
        m["text"]
        for m in customer["messages"]
        if m["role"] == "assistant" and m.get("request_id") == inbox["id"]
    ]
    prompt_text = "\n".join(prompt["lines"])
    if prompt_text and (not answers or answers[-1] != prompt_text):
        answers.append(prompt_text)
    lines = "\n".join(answers).splitlines()
    messages = []
    # Preserve long answers across separate floor-sized messages; never truncate facts.
    for start in range(0, max(len(lines), 1), 3):
        key = inbox["id"] + "-" + str(start // 3)
        message = OutgoingMessage(
            id=key,
            recipient=inbox["owner"],
            customer_id=customer["id"],
            version=customer["version"],
            lines=lines[start : start + 3] or ["Continue your visit."],
            buttons=prompt["buttons"] if start + 3 >= len(lines) else [],
        )
        put(
            db,
            "messaging_outbox",
            {
                "id": key,
                "owner": inbox["owner"],
                "provider": inbox["provider"],
                "message": message.model_dump(),
                "status": "pending",
                "attempts": 0,
                "created_at": now(),
                "lease_until": 0,
                "previous_id": messages[-1] if messages else None,
            },
        )
        messages.append(key)
    inbox.update(status="completed", outbox_ids=messages, lease_until=0)
    put(db, "messaging_inbox", inbox)
    return inbox


async def receive(event: IncomingMessage, user: dict, adapter: MessagingAdapter):
    """Persist normalized input, apply the journey once, then attempt delivery."""
    key = event_key(adapter.name, user["id"], event.event_id)
    payload = event.model_dump()
    with transaction() as db:
        customer = domain.owned(db, "customers", event.customer_id, user)
        inbox = get(db, "messaging_inbox", key)
        if inbox and inbox["payload"] != payload:
            raise HTTPException(409, "Event ID already used with different content")
        if inbox and inbox["status"] == "completed":
            return inbox
        if inbox and inbox.get("lease_until", 0) > time.time():
            raise HTTPException(409, "Event is already processing")
        if any(
            i["payload"]["customer_id"] == event.customer_id
            and i["id"] != key
            and i.get("lease_until", 0) > time.time()
            for i in read_all(db, "messaging_inbox")
        ):
            raise HTTPException(409, "Another message is processing for this visit")
        # A retry may recover an already committed AI/text response after a crash.
        recovered = any(
            m.get("request_id") == key and m["role"] == "assistant" for m in customer["messages"]
        )
        if not recovered:
            expected = inbox.get("retry_version", event.version) if inbox else event.version
            if inbox and inbox["status"] == "processing":
                # A process may die after the text service saves its pending input.
                pending = next(
                    (
                        m
                        for m in customer["messages"]
                        if m.get("request_id") == key and m["role"] == "user"
                    ),
                    {},
                )
                expected = pending.get("processing_version", expected)
            domain.require(
                customer["version"] == expected,
                "Visit changed. Refresh and submit a new event ID/version.",
            )
        inbox = inbox or {
            "id": key,
            "owner": user["id"],
            "provider": adapter.name,
            "payload": payload,
            "created_at": now(),
            "outbox_ids": [],
        }
        inbox.update(status="processing", lease_until=time.time() + 120)
        put(db, "messaging_inbox", inbox)
        if recovered:
            inbox = enqueue(db, inbox, customer)
        elif event.kind == "action":
            domain.act(db, customer, user, event.action, validate(event.action, event.data))
            flow.append_prompt(db, customer)
            inbox = enqueue(db, inbox, customer)
        else:
            # Deterministic text commands and their outbox commit atomically.
            from app.web.intelligence import unsafe

            domain.message(customer, "user", event.text, request_id=key, actor=user["name"])
            customer.pop("chat_override", None)
            customer.pop("chat_override_text", None)
            if not unsafe(event.text) and flow.handle_text(db, customer, event.text, user, key):
                inbox = enqueue(db, inbox, customer)
            # For AI text, the existing message service persists its own user message.
            # The unsaved local object above is intentionally discarded.
    if inbox["status"] != "completed":
        try:
            from app.web.api import TextInput, process_message

            await process_message(
                event.customer_id,
                TextInput(
                    text=event.text,
                    request_id=key,
                    expected_version=expected,
                ),
                user,
            )
            with transaction() as db:
                customer = domain.owned(db, "customers", event.customer_id, user)
                inbox = enqueue(db, inbox, customer)
        except BaseException:
            with transaction() as db:
                current = domain.owned(db, "customers", event.customer_id, user)
                retry_version = expected
                for message in current["messages"]:
                    if message.get("request_id") == key and message["role"] == "user":
                        message["busy_until"] = 0
                        retry_version = message.get("processing_version", expected)
                put(db, "customers", current)
                # Only our own pending-message write can advance the retry version.
                # A concurrent website edit must still cause a stale-version rejection.
                inbox.update(
                    status="retryable",
                    lease_until=0,
                    retry_version=retry_version,
                )
                put(db, "messaging_inbox", inbox)
            raise
    for message_id in inbox["outbox_ids"]:
        sent = await dispatch(message_id, user, adapter)
        if sent["status"] not in ("accepted", "delivered", "read"):
            break
    return inbox


async def dispatch(message_id: str, user: dict, adapter: MessagingAdapter):
    """Retry transport only; never execute the business action again."""
    attempt = uid()
    with transaction() as db:
        item = owned_record(db, "messaging_outbox", message_id, user)
        domain.require(
            item["provider"] == adapter.name, "Use the original provider for this message"
        )
        if item["status"] in ("accepted", "delivered", "read"):
            return item
        if item.get("previous_id"):
            previous = get(db, "messaging_outbox", item["previous_id"])
            domain.require(
                previous["status"] in ("accepted", "delivered", "read"),
                "Retry the preceding reply first",
            )
        domain.require(item.get("lease_until", 0) <= time.time(), "Send already in progress")
        item.update(
            status="sending",
            lease_until=time.time() + 45,
            attempt=attempt,
            attempts=item["attempts"] + 1,
        )
        put(db, "messaging_outbox", item)
    try:
        receipt = SendReceipt.model_validate(
            await asyncio.wait_for(
                adapter.send(
                    OutgoingMessage.model_validate(item["message"]), idempotency_key=message_id
                ),
                timeout=15,
            )
        )
    except (TimeoutError, ProviderUnavailable, ValidationError, ValueError):
        with transaction() as db:
            current = get(db, "messaging_outbox", message_id)
            if current.get("attempt") == attempt and current["status"] not in ("delivered", "read"):
                current.update(
                    status="retryable",
                    lease_until=0,
                    error="Transport unavailable or response unverified; retry with the same ID.",
                )
                put(db, "messaging_outbox", current)
            return current
    except BaseException:
        with transaction() as db:
            current = get(db, "messaging_outbox", message_id)
            if current.get("attempt") == attempt and current["status"] not in ("delivered", "read"):
                current.update(status="retryable", lease_until=0)
                put(db, "messaging_outbox", current)
        raise
    with transaction() as db:
        current = get(db, "messaging_outbox", message_id)
        if current.get("attempt") == attempt:
            current.update(
                status=current["status"]
                if current["status"] in ("delivered", "read")
                else "accepted",
                receipt=receipt.model_dump(),
                lease_until=0,
            )
            current.pop("error", None)
            put(db, "messaging_outbox", current)
            audit(db, user["id"], "messaging_accepted", message_id)
        return current


def delivery(message_id: str, update: DeliveryUpdate, user: dict, provider: str):
    with transaction() as db:
        item = owned_record(db, "messaging_outbox", message_id, user)
        domain.require(item["provider"] == provider, "Provider mismatch")
        domain.require(
            item.get("receipt", {}).get("provider_message_id") == update.provider_message_id,
            "Unknown provider receipt",
        )
        rank = {
            "pending": 0,
            "sending": 0,
            "retryable": 0,
            "accepted": 1,
            "failed": 2,
            "delivered": 3,
            "read": 4,
        }
        if rank[update.status] > rank[item["status"]]:
            item.update(status=update.status, delivery_updated_at=now())
            put(db, "messaging_outbox", item)
            audit(db, user["id"], "messaging_" + update.status, message_id)
        return item
