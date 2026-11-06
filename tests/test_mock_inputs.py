import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx

from app.ai.provider import MockAIProvider, get_ai_provider
from app.catalog.provider import EmptyCatalogProvider, get_catalog
from app.core.config import get_settings
from app.db.models import StoreSession
from app.db.session import get_db
from app.legacy import create_app
from app.meta.client import MetaClient
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.corpus import chunk_documents, load_documents
from app.retrieval.provider import get_retriever


class MemorySession:
    """Persistence substitute for route wiring checks, not a PostgreSQL test."""

    def __init__(self):
        self.session = StoreSession(
            id=uuid4(),
            associate_id="test",
            store_id="test-store",
            language="en",
            stage="assess",
            home_card={},
        )
        self.messages = []

    async def get(self, model, session_id):
        return self.session if session_id == self.session.id else None

    async def scalars(self, statement):
        return list(reversed(self.messages))

    def add_all(self, messages):
        self.messages.extend(messages)

    async def commit(self):
        for message in self.messages:
            if message.id is None:
                message.id = uuid4()


class MockInputTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.object(get_settings(), "enable_dev_routes", True):
            self.app = create_app()
        self.db = MemorySession()
        corpus = Path(__file__).resolve().parents[1] / "fixtures/knowledge_base/documents.json"
        retriever = BM25Retriever(chunk_documents(load_documents(corpus)))

        async def database():
            yield self.db

        self.app.dependency_overrides.update(
            {
                get_db: database,
                get_ai_provider: lambda: MockAIProvider(),
                get_catalog: lambda: EmptyCatalogProvider(),
                get_retriever: lambda: retriever,
            }
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://local"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_whatsapp_mock_retrieves_and_persists_without_meta_delivery(self):
        send = AsyncMock(side_effect=AssertionError("No Meta send is allowed"))
        with (
            patch.object(get_settings(), "meta_mode", "live"),
            patch.object(MetaClient, "send_text", send),
        ):
            response = await self.client.post(
                "/api/v1/dev/mock-whatsapp-text",
                json={
                    "session_id": str(self.db.session.id),
                    "sender": "15550100001",
                    "mock_whatsapp_text": "TV viewing distance from the sofa",
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["inbound"]["type"], "text")
        self.assertEqual(body["inbound"]["from"], "15550100001")
        self.assertEqual(body["outbound"]["mode"], "mock")
        self.assertEqual(body["coaching"]["knowledge"]["status"], "matched")
        self.assertEqual(len(self.db.messages), 2)
        self.assertEqual(self.db.messages[0].source, "mock_whatsapp_text")
        self.assertEqual(self.db.messages[0].details["transport"], "mock")
        self.assertEqual(self.db.messages[1].details["knowledge"], body["coaching"]["knowledge"])
        self.assertLessEqual(len(body["outbound"]["text"].splitlines()), 3)
        send.assert_not_awaited()

    async def test_voice_and_plain_text_also_use_retrieval(self):
        for route, field in [
            ("/api/v1/dev/mock-recordings", "mock_recording_text"),
            (f"/api/v1/sessions/{self.db.session.id}/messages", "text"),
        ]:
            response = await self.client.post(
                route,
                json={
                    "session_id": str(self.db.session.id),
                    field: "TV viewing distance",
                },
            )
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["knowledge"]["status"], "matched")

    async def test_retrieval_search_does_not_need_a_database(self):
        async def forbidden_database():
            raise AssertionError("Retrieval search must not access the DB")

        self.app.dependency_overrides[get_db] = forbidden_database
        response = await self.client.post(
            "/api/v1/dev/retrieval/search",
            json={
                "query": "viewing distance",
                "store_id": "test-store",
                "top_k": 1,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["hits"]), 1)

    async def test_empty_text_and_missing_sessions_fail_before_saving(self):
        for session_id, text, status in [
            (self.db.session.id, "   ", 422),
            (uuid4(), "TV", 404),
        ]:
            response = await self.client.post(
                "/api/v1/dev/mock-whatsapp-text",
                json={
                    "session_id": str(session_id),
                    "mock_whatsapp_text": text,
                },
            )
            self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(self.db.messages, [])
