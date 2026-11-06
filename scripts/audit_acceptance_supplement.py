"""Independent real-HTTP expert, security, replay and concurrency checks."""

import concurrent.futures
import json
import time
from pathlib import Path

import httpx

OUT = Path("output/contest-acceptance-2026-11-05")
rows = []
client = httpx.Client(base_url="http://127.0.0.1:8011", timeout=60)


def req(label, method, path, body=None, expected=200):
    start = time.perf_counter()
    r = client.request(method, path, json=body)
    rows.append(
        dict(
            label=label,
            status=r.status_code,
            expected=expected,
            seconds=round(time.perf_counter() - start, 3),
            response=r.json(),
        )
    )
    (OUT / "supplement.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return r.json()


def login(admin=False):
    return req(
        "admin login" if admin else "associate login",
        "POST",
        "/api/auth/login",
        dict(
            phone="9000000009" if admin else "9000000002",
            password="Admin@123" if admin else "Associate@123",
        ),
    )


login()
c = req("new expert customer", "POST", "/api/customers", {"name": "Audit expert lifecycle"}, 201)
r = req(
    "blocking expert request",
    "POST",
    "/api/requests",
    dict(
        customer_id=c["id"],
        question="Confirm specialist installation compatibility from approved site report",
        blocking=True,
    ),
    201,
)
req(
    "duplicate expert request",
    "POST",
    "/api/requests",
    dict(customer_id=c["id"], question=r["question"], blocking=True),
    201,
)
req(
    "associate cannot answer as admin",
    "POST",
    f"/api/requests/{r['id']}/reply",
    {"text": "Not allowed"},
    403,
)
login(True)
req(
    "assign expert",
    "POST",
    f"/api/requests/{r['id']}/action",
    dict(action="assign", version=1, data={"owner": "Priya Desai"}),
)
req(
    "attributed admin answer",
    "POST",
    f"/api/requests/{r['id']}/reply",
    {"text": "Site compatibility remains unconfirmed. Await verified specialist site report."},
)
login()
req("associate notifications", "GET", "/api/bootstrap")
req(
    "resolve without evidence",
    "POST",
    f"/api/requests/{r['id']}/action",
    dict(action="resolve", version=1, data={}),
)
req(
    "reopen same expert thread",
    "POST",
    "/api/requests",
    dict(customer_id=c["id"], question=r["question"], blocking=True),
    201,
)
c = req("refresh expert customer", "GET", f"/api/customers/{c['id']}")
payload = dict(text="Hindi", request_id="audit-supplement-replay")
req("first deterministic message", "POST", f"/api/customers/{c['id']}/messages", payload)
req("same request replay", "POST", f"/api/customers/{c['id']}/messages", payload)
req(
    "request id reused with different text",
    "POST",
    f"/api/customers/{c['id']}/messages",
    {**payload, "text": "No consent"},
)
req(
    "stale action rejected",
    "POST",
    f"/api/customers/{c['id']}/actions",
    dict(action="consent", version=1, data={"given": True}),
    409,
)
req("invalid date rejected", "GET", "/api/bootstrap?start=2026-02-30", expected=422)
req(
    "reversed dates rejected", "GET", "/api/bootstrap?start=2026-11-05&end=2026-11-01", expected=422
)
req(
    "blank message rejected",
    "POST",
    f"/api/customers/{c['id']}/messages",
    {"text": "", "request_id": "blank"},
    422,
)
r = client.post(
    "/api/customers", json={"name": "Bad origin"}, headers={"Origin": "https://evil.example"}
)
rows.append(
    dict(label="cross origin rejected", status=r.status_code, expected=403, response=r.json())
)


def probe(i):
    start = time.perf_counter()
    r = httpx.get("http://127.0.0.1:8011/health/ready")
    return dict(index=i, status=r.status_code, seconds=round(time.perf_counter() - start, 3))


with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    readings = list(pool.map(probe, range(20)))
(OUT / "concurrent-readiness.json").write_text(json.dumps(readings, indent=2), encoding="utf-8")
(OUT / "supplement.json").write_text(
    json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"{len(rows)} supplemental HTTP checks; 20 readiness requests at concurrency 5")
