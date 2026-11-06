"""Adapter factory. Unknown/unimplemented providers fail closed."""

from fastapi import HTTPException

from app.core.config import get_settings
from app.messaging.contracts import IncomingMessage, OutgoingMessage, SendReceipt
from app.web.store import get, now, put, transaction


class MockWhatsAppAdapter:
    name = "mock"

    def decode(self, payload: bytes, headers: dict[str, str]) -> IncomingMessage:
        return IncomingMessage.model_validate_json(payload)

    async def send(self, message: OutgoingMessage, *, idempotency_key: str) -> SendReceipt:
        # Persist the receipt to make retries/restarts observable and idempotent.
        # This adapter never imports a network client or contacts WhatsApp.
        with transaction() as db:
            existing = get(db, "messaging_mock_receipts", idempotency_key)
            if existing:
                if existing["message"] != message.model_dump():
                    raise ValueError("Idempotency key reused with a different message")
                return SendReceipt.model_validate(existing["receipt"])
            receipt = SendReceipt(provider_message_id="mock-" + idempotency_key, simulated=True)
            put(
                db,
                "messaging_mock_receipts",
                {
                    "id": idempotency_key,
                    "message": message.model_dump(),
                    "receipt": receipt.model_dump(),
                    "created_at": now(),
                },
            )
            return receipt


def get_adapter():
    provider = get_settings().whatsapp_provider
    if provider == "mock":
        return MockWhatsAppAdapter()
    raise HTTPException(503, f"WhatsApp provider '{provider}' is not implemented or is disabled")
