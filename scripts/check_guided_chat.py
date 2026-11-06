"""Paid live check of home extraction and guided/expert interruption; synthetic data only."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.message_polling import TextPollingClient as TestClient

from app.main import create_app
from app.web import store

if "--live" not in sys.argv:
    raise SystemExit("Use --live to explicitly enable real OpenAI calls.")
sys.stdout.reconfigure(encoding="utf-8")
with store.transaction() as db:
    published = store.get(db, "index", "status")
assert published and not published["dirty"], "Rebuild the app's knowledge index first"
with tempfile.TemporaryDirectory() as directory:
    with patch.object(store, "DB_PATH", Path(directory) / "guided.db"):
        with TestClient(create_app()) as client:
            assert (
                client.post(
                    "/api/auth/login", json={"phone": "9000000001", "password": "Associate@123"}
                ).status_code
                == 200
            )
            with store.transaction() as db:
                store.put(db, "index", published)
            c = client.post("/api/customers", json={"name": "Guided synthetic check"}).json()
            assert c["flow"]["question"] == "distance"
            response = client.post(
                f"/api/customers/{c['id']}/messages",
                json={
                    "text": "Viewing distance 9 feet. Bright daylight. Cricket and movies. Family sits on sides. Wants to fix motion blur. Wall mounting. Budget 70000 rupees.",
                    "request_id": "natural-home",
                },
            )
            assert response.status_code == 200, response.text
            c = response.json()
            assert c["flow"]["question"] is None, c["home"]
            assert [b["label"] for b in c["flow"]["buttons"]] == ["Correct", "Edit", "Ask customer"]
            print("Natural home extraction: all seven facts saved; confirmation buttons shown.")

            def act(action, data=None):
                result = client.post(
                    f"/api/customers/{c['id']}/actions",
                    json={"action": action, "data": data or {}, "version": c["version"]},
                )
                assert result.status_code == 200, result.text
                return result.json()

            c = act("confirm_home")
            assert [b["label"] for b in c["flow"]["buttons"]] == [
                "Demo A/B",
                "Change options",
                "Stock details",
            ]
            saved_stage = c["stage"]
            c = act("ask_expert")
            response = client.post(
                f"/api/customers/{c['id']}/messages",
                json={
                    "text": "What is the native refresh rate of Samsung Vision Q55?",
                    "request_id": "expert-check",
                },
            )
            assert response.status_code == 200, response.text
            c = response.json()
            answer = c["messages"][-1]
            assert "120" in answer["text"], answer["text"]
            assert answer["sources"]
            assert c["stage"] == saved_stage
            assert [b["label"] for b in c["flow"]["buttons"]] == [
                "Resolved",
                "Ask admin",
                "Ask follow-up",
            ]
            print("Grounded expert interruption:", answer["text"])
            c = act("expert_resolved")
            assert c["stage"] == saved_stage
            assert c["flow"]["buttons"][0]["label"] == "Demo A/B"
            c = act("start_demo")
            assert [b["label"] for b in c["flow"]["buttons"]] == [
                "Demo done",
                "Need another demo",
                "Demo unavailable",
            ]
            assert c["demo"] is None and not c["sale"]
            print(
                "Return to saved step and physical-demo buttons: passed; demo and sale remain unconfirmed."
            )
