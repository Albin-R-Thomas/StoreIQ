"""Sample documented natural-language interruptions against configured live AI."""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from scripts.message_polling import TextPollingClient as TestClient

from app.main import create_app
from app.web import store

if "--live" not in sys.argv:
    raise SystemExit("Pass --live for real provider requests.")
with store.transaction() as db:
    published = store.get(db, "index", "status")
results = []
with (
    tempfile.TemporaryDirectory() as directory,
    patch.object(store, "DB_PATH", Path(directory) / "live-review.db"),
):
    with TestClient(create_app()) as client:
        assert (
            client.post(
                "/api/auth/login", json={"phone": "9000000001", "password": "Associate@123"}
            ).status_code
            == 200
        )
        with store.transaction() as db:
            store.put(db, "index", published)
        c = client.post("/api/customers", json={"name": "Live reviewer synthetic visitor"}).json()
        for i, text in enumerate(
            [
                "What is the current price of Samsung Vision Q55? "
                "The customer asked price before answering the home questions.",
                "Customer says every 4K TV gives the same picture. What should I say?",
                "Explain Samsung Vision Q55 HDMI 2.1 for this customer.",
                "Explain model XYZ-UNKNOWN-999. Do not assume it is a known TV.",
                "Customers from 5 Nov 2026 to 1 Nov 2026",
                "Change options to a smaller size from another brand",
            ]
        ):
            start = time.monotonic()
            r = client.post(
                f"/api/customers/{c['id']}/messages",
                json={"text": text, "request_id": f"reviewer-{i}"},
            )
            body = r.json()
            results.append(
                dict(
                    input=text,
                    status=r.status_code,
                    seconds=round(time.monotonic() - start, 2),
                    answer=body["messages"][-1] if r.status_code == 200 else body,
                    home=body.get("home"),
                    flow=body.get("flow", {}).get("lines"),
                )
            )
            if r.status_code == 200:
                c = body
            print(f"Live scenario {i + 1}: {r.status_code}", flush=True)
Path("output/live-review-evidence.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
