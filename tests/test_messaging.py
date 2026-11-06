"""Real HTTP/SQLite mock channel tests. No WhatsApp or AI network access."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core.config import get_settings
from app.messaging import service
from app.messaging.adapters import MockWhatsAppAdapter, get_adapter
from app.messaging.contracts import IncomingMessage, ProviderUnavailable, SendReceipt
from app.web import store
from tests import test_web_journey as journey


class MessagingTests(unittest.TestCase):
    login = journey.WebJourneyTests.login
    customer = journey.WebJourneyTests.customer
    act = journey.WebJourneyTests.act
    ready_customer = journey.WebJourneyTests.ready_customer

    def setUp(self):
        self.env = patch.dict(os.environ, {"DEMO_MODE": "true"})
        self.env.start()
        self.settings = patch.multiple(
            get_settings(), enable_dev_routes=True, whatsapp_provider="mock"
        )
        self.settings.start()
        journey.WebJourneyTests.setUp(self)
        self.network = patch(
            "app.web.intelligence.client",
            side_effect=AssertionError("Unexpected AI network request"),
        )
        self.network.start()

    def tearDown(self):
        self.network.stop()
        journey.WebJourneyTests.tearDown(self)
        self.settings.stop()
        self.env.stop()

    def event(self, c, event_id=None, **values):
        return {
            "event_id": event_id or c["id"],
            "customer_id": c["id"],
            "version": c["version"],
            "kind": "action",
            "action": "ask_home",
            **values,
        }

    def send(self, payload, status=200):
        result = self.client.post("/api/messaging/mock/events", json=payload)
        self.assertEqual(result.status_code, status, result.text)
        return result.json()

    def saved(self, c):
        return self.client.get(f"/api/customers/{c['id']}").json()

    def test_text_journey_web_resume_and_duplicate_replay(self):
        c = self.customer()
        payload = self.event(c)
        first = self.send(payload)
        self.assertTrue(first["simulated"])
        self.assertEqual(first["messages"][0]["status"], "accepted")
        self.assertTrue(first["messages"][0]["receipt"]["simulated"])
        after = self.saved(c)
        self.assertEqual(self.send(payload), first)
        self.assertEqual(self.saved(c)["version"], after["version"])
        result = self.send(self.event(after, "distance", kind="text", action="", text="8 feet"))
        self.assertEqual(self.saved(c)["home"]["distance"], "8 feet")
        for item in result["messages"]:
            self.assertLessEqual(len(item["message"]["lines"]), 3)
            self.assertLessEqual(len(item["message"]["buttons"]), 3)
        # Reconstruct adapter after a restart: durable mock receipt stays the same.
        item = first["messages"][0]
        retried = asyncio.run(
            service.dispatch(
                item["id"], self.client.get("/api/auth/me").json(), MockWhatsAppAdapter()
            )
        )
        self.assertEqual(retried["receipt"], item["receipt"])

    def test_stale_conflicting_and_invalid_events_do_not_mutate(self):
        c = self.customer()
        payload = self.event(c)
        self.send(payload)
        self.send({**payload, "action": "end_visit"}, 409)
        self.send({**payload, "event_id": "out-of-order"}, 409)
        current = self.saved(c)
        self.send(self.event(current, "invalid", action="sale", data={}), 422)
        self.send(self.event(current, "unsupported", kind="audio"), 422)
        self.send(self.event(current, "empty", kind="text", action="", text=" "), 422)
        self.assertEqual(self.saved(c)["version"], current["version"])

    def test_authorization_and_mock_disable(self):
        c = self.customer()
        result = self.send(self.event(c))
        message_id = result["messages"][0]["id"]
        self.login("9000000002")
        self.send(self.event(c), 403)
        self.assertEqual(self.client.get("/api/messaging/mock/outbox").json()["messages"], [])
        self.assertEqual(
            self.client.post(f"/api/messaging/mock/outbox/{message_id}/retry").status_code, 403
        )
        with patch.object(get_settings(), "enable_dev_routes", False):
            self.assertEqual(self.client.get("/api/messaging/mock/outbox").status_code, 404)
        with patch.dict(os.environ, {"DEMO_MODE": "false"}):
            self.assertEqual(self.client.get("/api/messaging/mock/outbox").status_code, 404)
        self.client.post("/api/auth/logout")
        self.send(self.event(c), 401)
        with patch.object(get_settings(), "whatsapp_provider", "twilio"):
            with self.assertRaises(HTTPException) as error:
                get_adapter()
            self.assertEqual(error.exception.status_code, 503)

    def test_sale_and_stock_are_not_repeated_by_duplicate_or_transport_retry(self):
        c = self.ready_customer()
        c = self.act(c, "payment", {"method": "full"})
        quote = self.client.get(f"/api/customers/{c['id']}/summary").json()
        payload = self.event(c, "sale", action="sale", data={"confirmed_total": quote["total"]})
        with patch.object(
            MockWhatsAppAdapter, "send", new=AsyncMock(side_effect=ProviderUnavailable())
        ):
            first = self.send(payload)
        self.assertEqual(first["messages"][0]["status"], "retryable")
        with store.transaction() as db:
            stock = store.get(db, "products", c["preferred"])["stock"]
        self.send(payload)
        message_id = first["messages"][0]["id"]
        retry = self.client.post(f"/api/messaging/mock/outbox/{message_id}/retry")
        self.assertEqual(retry.json()["status"], "accepted")
        with store.transaction() as db:
            self.assertEqual(store.get(db, "products", c["preferred"])["stock"], stock)
            self.assertEqual(
                len([t for t in store.read_all(db, "tasks") if t["customer_id"] == c["id"]]), 3
            )

    def test_timeout_malformed_receipt_and_partial_send_recover(self):
        for error in (TimeoutError(), ProviderUnavailable()):
            with self.subTest(error=type(error).__name__):
                c = self.customer()
                with patch.object(MockWhatsAppAdapter, "send", new=AsyncMock(side_effect=error)):
                    result = self.send(self.event(c))
                item = result["messages"][0]
                self.assertEqual(item["status"], "retryable")
                response = self.client.post(f"/api/messaging/mock/outbox/{item['id']}/retry")
                self.assertEqual(response.json()["status"], "accepted")
        c = self.customer()
        with patch.object(MockWhatsAppAdapter, "send", new=AsyncMock(return_value={"bad": True})):
            item = self.send(self.event(c))["messages"][0]
        self.assertEqual(item["status"], "retryable")
        original = MockWhatsAppAdapter.send

        async def accept_then_timeout(adapter, message, *, idempotency_key):
            await original(adapter, message, idempotency_key=idempotency_key)
            raise TimeoutError()

        with patch.object(MockWhatsAppAdapter, "send", new=accept_then_timeout):
            self.client.post(f"/api/messaging/mock/outbox/{item['id']}/retry")
        response = self.client.post(f"/api/messaging/mock/outbox/{item['id']}/retry")
        self.assertEqual(response.json()["status"], "accepted")
        with store.transaction() as db:
            self.assertEqual(
                len(
                    [
                        r
                        for r in store.read_all(db, "messaging_mock_receipts")
                        if r["id"] == item["id"]
                    ]
                ),
                1,
            )

    def test_delivery_updates_are_monotonic_and_receipt_bound(self):
        item = self.send(self.event(self.customer()))["messages"][0]
        url = f"/api/messaging/mock/outbox/{item['id']}/delivery"
        update = {"provider_message_id": item["receipt"]["provider_message_id"], "status": "read"}
        self.assertEqual(self.client.post(url, json=update).json()["status"], "read")
        for status in ("delivered", "failed", "read"):
            self.assertEqual(
                self.client.post(url, json={**update, "status": status}).json()["status"], "read"
            )
        self.assertEqual(
            self.client.post(url, json={**update, "provider_message_id": "unknown"}).status_code,
            409,
        )

    def test_ai_failure_retry_preserves_one_user_message(self):
        c = self.ready_customer()
        payload = self.event(c, "ai", kind="text", action="", text="What is local dimming?")
        with patch(
            "app.web.intelligence.answer",
            new=AsyncMock(side_effect=HTTPException(502, "Provider unavailable")),
        ):
            self.send(payload, 502)
        with patch(
            "app.web.intelligence.answer",
            new=AsyncMock(
                return_value={
                    "text": "Not enough facts present.",
                    "sources": [],
                    "trace": {"mode": "test"},
                }
            ),
        ):
            self.send(payload)
        messages = self.saved(c)["messages"]
        self.assertEqual(
            sum(m["role"] == "user" and m["text"] == payload["text"] for m in messages), 1
        )

    def test_cancellation_releases_transport_lease(self):
        c = self.customer()
        with patch.object(
            MockWhatsAppAdapter, "send", new=AsyncMock(side_effect=ProviderUnavailable())
        ):
            item = self.send(self.event(c))["messages"][0]
        user = self.client.get("/api/auth/me").json()
        with patch.object(
            MockWhatsAppAdapter, "send", new=AsyncMock(side_effect=asyncio.CancelledError())
        ):
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(service.dispatch(item["id"], user, MockWhatsAppAdapter()))
        self.assertEqual(
            asyncio.run(service.dispatch(item["id"], user, MockWhatsAppAdapter()))["status"],
            "accepted",
        )

    def test_adapter_swap_keeps_business_calls_unchanged(self):
        class AlternateAdapter:
            name = "alternate"

            async def send(self, message, *, idempotency_key):
                return SendReceipt(
                    provider_message_id="alternate-" + idempotency_key, simulated=True
                )

        c = self.customer()
        user = self.client.get("/api/auth/me").json()
        result = asyncio.run(
            service.receive(IncomingMessage(**self.event(c)), user, AlternateAdapter())
        )
        with store.transaction() as db:
            item = store.get(db, "messaging_outbox", result["outbox_ids"][0])
        self.assertEqual(item["provider"], "alternate")
        self.assertTrue(item["receipt"]["provider_message_id"].startswith("alternate-"))
        self.assertEqual(self.saved(c)["awaiting_home"], "distance")

    def test_pending_ai_retry_rejects_concurrent_web_edit(self):
        c = self.ready_customer()
        payload = self.event(c, "ai-stale", kind="text", action="", text="What is local dimming?")

        async def fail_after_edit(*args, **kwargs):
            with store.transaction() as db:
                current = store.get(db, "customers", c["id"])
                current["version"] += 1
                current["notes"].append("Concurrent website edit")
                store.put(db, "customers", current)
            raise HTTPException(502, "Provider unavailable")

        with patch("app.web.intelligence.answer", new=fail_after_edit):
            self.send(payload, 502)
        self.send(payload, 409)
        self.assertIn("Concurrent website edit", self.saved(c)["notes"])

    def test_expired_processing_lease_recovers_pending_ai_message(self):
        c = self.ready_customer()
        payload = self.event(c, "ai-restart", kind="text", action="", text="What is local dimming?")
        with patch(
            "app.web.intelligence.answer",
            new=AsyncMock(side_effect=HTTPException(502, "Provider unavailable")),
        ):
            self.send(payload, 502)
        key = service.event_key("mock", "associate-1", payload["event_id"])
        with store.transaction() as db:
            inbox = store.get(db, "messaging_inbox", key)
            inbox.update(status="processing", lease_until=0)
            inbox.pop("retry_version", None)
            store.put(db, "messaging_inbox", inbox)
        with patch(
            "app.web.intelligence.answer",
            new=AsyncMock(
                return_value={
                    "text": "Not enough facts present.",
                    "sources": [],
                    "trace": {"mode": "test"},
                }
            ),
        ):
            self.send(payload)
        self.assertEqual(
            sum(
                m["role"] == "user" and m.get("request_id") == key
                for m in self.saved(c)["messages"]
            ),
            1,
        )

    def test_multi_part_reply_preserves_content_and_send_order(self):
        c = self.ready_customer()
        payload = self.event(c, "parts", kind="text", action="", text="What is local dimming?")
        with (
            patch(
                "app.web.intelligence.answer",
                new=AsyncMock(
                    return_value={
                        "text": "First fact.\nSecond fact.\nThird fact.",
                        "sources": [],
                        "trace": {"mode": "test"},
                    }
                ),
            ),
            patch.object(MockWhatsAppAdapter, "send", new=AsyncMock(side_effect=TimeoutError())),
        ):
            result = self.send(payload)
        first, second = result["messages"]
        self.assertEqual(first["message"]["lines"], ["First fact.", "Second fact.", "Third fact."])
        self.assertEqual(second["status"], "pending")
        path = "/api/messaging/mock/outbox/"
        self.assertEqual(self.client.post(path + second["id"] + "/retry").status_code, 409)
        self.assertEqual(
            self.client.post(path + first["id"] + "/retry").json()["status"], "accepted"
        )
        self.assertEqual(
            self.client.post(path + second["id"] + "/retry").json()["status"], "accepted"
        )

    def test_late_read_callback_during_retry_cannot_be_downgraded(self):
        item = self.send(self.event(self.customer()))["messages"][0]
        user = self.client.get("/api/auth/me").json()
        from app.messaging.contracts import DeliveryUpdate

        receipt_id = item["receipt"]["provider_message_id"]
        service.delivery(
            item["id"],
            DeliveryUpdate(provider_message_id=receipt_id, status="failed"),
            user,
            "mock",
        )

        async def read_during_send(message, *, idempotency_key):
            service.delivery(
                item["id"],
                DeliveryUpdate(provider_message_id=receipt_id, status="read"),
                user,
                "mock",
            )
            return SendReceipt(provider_message_id=receipt_id, simulated=True)

        with patch.object(MockWhatsAppAdapter, "send", new=AsyncMock(side_effect=read_during_send)):
            result = asyncio.run(service.dispatch(item["id"], user, MockWhatsAppAdapter()))
        self.assertEqual(result["status"], "read")
