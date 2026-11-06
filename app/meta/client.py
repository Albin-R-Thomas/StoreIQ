from uuid import uuid4

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import IntegrationFailure, IntegrationNotConfigured


class SendResult(BaseModel):
    mode: str
    message_id: str
    recipient: str


class MetaClient:
    async def send_text(self, recipient: str, text: str) -> SendResult:
        settings = get_settings()
        if settings.meta_mode == "mock":
            # No HTTP request, including when credentials happen to exist in .env.
            return SendResult(mode="mock", message_id=f"mock-{uuid4()}", recipient=recipient)
        if recipient not in settings.meta_test_recipients:
            raise IntegrationNotConfigured("Recipient must be in META_TEST_RECIPIENTS.")
        if not all(
            [
                settings.meta_access_token.get_secret_value(),
                settings.meta_phone_number_id,
                settings.meta_api_version,
            ]
        ):
            raise IntegrationNotConfigured(
                "Configure META_ACCESS_TOKEN, META_PHONE_NUMBER_ID and META_API_VERSION."
            )
        url = (
            f"https://graph.facebook.com/{settings.meta_api_version}/"
            f"{settings.meta_phone_number_id}/messages"
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {settings.meta_access_token.get_secret_value()}"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": recipient,
                        "type": "text",
                        "text": {"preview_url": False, "body": text},
                    },
                )
                response.raise_for_status()
                message_id = response.json()["messages"][0]["id"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise IntegrationFailure("Meta send failed; inspect delivery before retrying.") from exc
        return SendResult(mode="live", message_id=message_id, recipient=recipient)


def get_meta_client() -> MetaClient:
    return MetaClient()
