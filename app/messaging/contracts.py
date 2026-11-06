"""Only adapters know provider payloads, authentication or transport APIs."""

import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IncomingMessage(Contract):
    event_id: str = Field(min_length=1, max_length=100)
    customer_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    kind: Literal["text", "action"] = "text"
    text: str = Field(default="", max_length=4000)
    action: str = Field(default="", max_length=40)
    data: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def payload(self):
        if len(json.dumps(self.data)) > 12000:
            raise ValueError("Action data too large")
        if self.kind == "text" and (not self.text.strip() or self.action or self.data):
            raise ValueError("Text events require text only")
        if self.kind == "action" and (not self.action or self.text):
            raise ValueError("Action events require an action and optional data only")
        return self


class ReplyButton(Contract):
    label: str
    kind: Literal["action", "input", "navigate"]
    name: str
    data: dict = Field(default_factory=dict)


class OutgoingMessage(Contract):
    id: str
    recipient: str
    customer_id: str
    version: int
    lines: list[str] = Field(min_length=1, max_length=3)
    buttons: list[ReplyButton] = Field(default_factory=list, max_length=3)


class SendReceipt(Contract):
    provider_message_id: str = Field(min_length=1, max_length=200)
    # Accepted by transport is not evidence of delivery to a phone.
    status: Literal["accepted"] = "accepted"
    simulated: bool


class DeliveryUpdate(Contract):
    provider_message_id: str = Field(min_length=1, max_length=200)
    status: Literal["delivered", "read", "failed"]


class MessagingAdapter(Protocol):
    name: str

    def decode(self, payload: bytes, headers: dict[str, str]) -> IncomingMessage:
        """Verify provider authenticity BEFORE normalizing an incoming message.

        Real adapters must resolve verified sender identity/customer context from
        trusted server bindings, never from caller-supplied associate IDs.
        The mock ingress instead uses the website's authenticated session.
        """
        ...

    async def send(self, message: OutgoingMessage, *, idempotency_key: str) -> SendReceipt:
        """Send once when supported; reconcile ambiguous provider timeouts.

        Preserve the key on retry. Providers without idempotent sends must look
        up/reconcile their own attempt before resending, or report uncertainty.
        """
        ...


class ProviderUnavailable(Exception):
    """Transport cannot currently accept a message."""
