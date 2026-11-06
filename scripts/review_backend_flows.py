"""Reviewer probes: real HTTP handlers and isolated SQLite; no frontend or AI stubs."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.web import store

HOME = dict(
    distance="9 feet",
    light="Bright daylight",
    use="Cricket and movies",
    seating="Sides",
    problem="Motion blur",
    placement="Wall",
    budget="70000",
)
evidence = []


def record(label, value):
    evidence.append(dict(scenario=label, observed=value))


with (
    tempfile.TemporaryDirectory() as directory,
    patch.object(store, "DB_PATH", Path(directory) / "review.db"),
):
    with TestClient(create_app()) as client:

        def login(admin=False):
            r = client.post(
                "/api/auth/login",
                json=dict(
                    phone="9000000009" if admin else "9000000001",
                    password="Admin@123" if admin else "Associate@123",
                ),
            )
            assert r.status_code == 200, r.text

        def new(name="Review visitor"):
            r = client.post("/api/customers", json={"name": name})
            assert r.status_code == 201, r.text
            return r.json()

        def act(c, action, data=None, expected=200):
            r = client.post(
                f"/api/customers/{c['id']}/actions",
                json=dict(version=c["version"], action=action, data=data or {}),
            )
            assert r.status_code == expected, (action, r.status_code, r.text)
            return r.json() if expected == 200 else c

        def ready(home=None):
            c = act(new(), "home", {"home": home or HOME})
            c = act(c, "confirm_home")
            c = act(
                c,
                "demo",
                dict(preferred=c["selected"][0], reason="Customer prefers cricket motion"),
            )
            return act(
                c,
                "site",
                dict(
                    placement="Wall",
                    specialist="no",
                    power="Socket checked",
                    cable_route="Route checked",
                    access="Access checked",
                    devices="Devices checked",
                    notes="Power cable wall access and devices checked",
                ),
            )

        def quote(c):
            return client.get(f"/api/customers/{c['id']}/summary").json()

        def fresh(c):
            return client.get(f"/api/customers/{c['id']}").json()

        login()
        record(
            "shift start/skip/invalid",
            [
                client.post("/api/shift", json={"text": t}).status_code
                for t in ["start", "skip_practice", "invalid"]
            ],
        )
        boot = client.get("/api/bootstrap").json()
        attempts = []
        for q in boot["questions"]:
            for choice in range(3):
                r = client.post("/api/training", json=dict(question_id=q["id"], choice=choice))
                assert r.status_code == 200
                attempts.append(r.json()["correct"])
        record(
            "training all six questions, every answer",
            dict(
                attempts=len(attempts),
                correct=sum(attempts),
                invalid=client.post(
                    "/api/training", json=dict(question_id="missing", choice=0)
                ).status_code,
            ),
        )
        c = ready()
        q = quote(c)
        c = act(c, "extras", {"extras": ["soundbar", "protection"]})
        record("optional extras add/remove", dict(base=q["total"], both=quote(c)["total"]))
        c = act(c, "extras", {"extras": []})
        c = act(c, "payment", {"method": "finance"})
        record("finance totals", quote(c))
        c = act(c, "sale", {"confirmed_total": quote(c)["finance"]["total"]})
        tasks = [
            t for t in client.get("/api/bootstrap").json()["tasks"] if t["customer_id"] == c["id"]
        ]
        update = dict(
            status="completed",
            detail="picture sound devices satisfaction all confirmed",
            assigned_to="Review owner",
            due_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        )
        for kind in ["delivery", "installation", "working_check"]:
            t = next(t for t in tasks if t["kind"] == kind)
            assert client.post("/api/tasks/" + t["id"], json=update).status_code == 200
        t = next(t for t in tasks if t["kind"] == "installation")
        update.update(status="pending", detail="Appointment now pending again")
        r = client.post("/api/tasks/" + t["id"], json=update)
        record(
            "reopen completed installation as pending",
            dict(status=r.status_code, stage=fresh(c)["stage"]),
        )
        c = ready()
        c = act(c, "home", {"home": {"placement": "Table"}})
        c = act(c, "confirm_home")
        c = act(c, "demo", dict(preferred=c["selected"][0], reason="Customer liked the picture"))
        record(
            "wall to table correction retains site",
            dict(home=c["home"]["placement"], site=c["site"], missing=quote(c)["missing"]),
        )
        c = ready()
        c = act(c, "language", {"language": "Hindi"})
        record("Hindi guided prompt", dict(language=c["language"], lines=c["flow"]["lines"]))
        c = act(c, "language", {"language": "Marathi"})
        record("Marathi guided prompt", c["flow"]["lines"])
        c = act(c, "end_visit")
        record("partial visit review", dict(lines=c["flow"]["lines"], score=c["score"]))
        c = ready()
        r = client.post(
            "/api/requests",
            json=dict(
                customer_id=c["id"],
                question="Specialist compatibility remains unknown",
                blocking=True,
            ),
        ).json()
        c = fresh(c)
        act(c, "payment", {"method": "full"}, 409)
        c = act(c, "expert_resolved")
        c = act(c, "payment", {"method": "full"}, 409)
        record(
            "associate resolves unanswered blocker", dict(payment=c["payment"], request_id=r["id"])
        )
        r2 = client.post(
            "/api/requests",
            json=dict(
                customer_id=c["id"],
                question="Specialist compatibility remains unknown",
                blocking=True,
            ),
        ).json()
        record(
            "Ask admin after resolution", dict(original=r["id"], new=r2["id"], number=r2["number"])
        )
        c = ready()
        c = act(c, "consent", {"given": True})
        r = client.post(
            f"/api/customers/{c['id']}/share",
            json=dict(version=c["version"], action="share", data={"confirmed": True}),
        )
        record("share without recipient or prior PDF", dict(status=r.status_code, body=r.json()))
        preview = client.post(
            f"/api/customers/{c['id']}/share-preview",
            json=dict(
                version=c["version"],
                action="preview",
                data={"recipient": "Synthetic review recipient"},
            ),
        ).json()
        r = client.post(
            f"/api/customers/{c['id']}/share",
            json=dict(
                version=c["version"],
                action="share",
                data={"confirmed": True, "preview_id": preview["id"]},
            ),
        )
        assert r.status_code == 201, r.text
        token = r.json()["path"].split("/")[-1]
        login(True)
        p = next(
            p for p in client.get("/api/bootstrap").json()["products"] if p["id"] == c["preferred"]
        )
        p["price"] += 1234
        assert client.put("/api/admin/products/" + p["id"], json=p).status_code == 200
        shared = client.get("/api/shared/" + token).json()
        record(
            "price update versus shared quote version",
            dict(
                outdated=shared["outdated"],
                shared_total=shared["total"],
                current_total=quote(c)["total"],
            ),
        )
        login()
        for budget in ["1000", "25000", "70 thousand", "70 हजार"]:
            c = act(new(), "home", {"home": {**HOME, "budget": budget}})
            c = act(c, "confirm_home")
            record(
                "recommendation budget " + budget,
                dict(selected=c["selected"], lines=c["flow"]["lines"]),
            )
        c = ready()
        due = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        c = act(
            c,
            "followup",
            dict(
                consent=False,
                due_at=due,
                reason="Waiting for family decision",
                owner="Review owner",
            ),
        )
        record(
            "internal follow-up consent",
            next(
                t
                for t in client.get("/api/bootstrap").json()["tasks"]
                if t["customer_id"] == c["id"]
            ),
        )
        # Age the clock-dependent record, then trigger reminder processing through HTTP.
        with store.transaction() as db:
            task = next(t for t in store.read_all(db, "tasks") if t["customer_id"] == c["id"])
            task["due_at"] = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
            store.put(db, "tasks", task)
        before = client.get("/api/bootstrap").json()
        after = client.get("/api/bootstrap").json()
        record(
            "overdue follow-up notifications",
            [n for n in after["notifications"] if n["customer_id"] == c["id"]],
        )
        record(
            "date filter scoped customers versus tasks",
            dict(
                customers=len(
                    client.get("/api/bootstrap?start=2000-01-01&end=2000-01-01").json()["customers"]
                ),
                tasks=len(
                    client.get("/api/bootstrap?start=2000-01-01&end=2000-01-01").json()["tasks"]
                ),
            ),
        )
        c = act(new(), "home", {"home": {**HOME, "budget": "30000"}})
        c = act(c, "confirm_home")
        record("one suitable TV", dict(selected=c["selected"], lines=c["flow"]["lines"]))
        act(
            c,
            "demo",
            dict(preferred=c["selected"][0], reason="Only available TV demonstrated"),
            200,
        )
        record("single TV physical demo accepted", 200)
        c = act(new(), "home", {"home": {k: "Unknown" for k in HOME}})
        c = act(c, "confirm_home")
        record(
            "unknown home answers accepted once",
            dict(confirmed=c["confirmed"], question=c["flow"]["question"]),
        )
        c = act(c, "select", {"products": ["samsung-q55", "tcl-q55"]})
        c = act(c, "start_demo")
        c = act(c, "demo_unavailable", {"reason": "Display screen is broken"})
        act(c, "offers", expected=409)
        record(
            "unavailable demo blocks offers",
            dict(demo=c["demo"], reason=c["demo_unavailable_reason"]),
        )
        c = act(c, "select", {"products": ["lg-u43"]})
        record(
            "single TV compare route",
            client.post("/api/comparison", json={"products": ["lg-u43"]}).status_code,
        )
        c = ready()
        c = act(c, "site", dict(placement="Wall", specialist="no", notes="maybe"), 422)
        record("non-evidential site confirmation", dict(site=c["site"], total=quote(c)["total"]))
        c = act(c, "payment", {"method": "full"})
        act(c, "sale", {"confirmed_total": 1}, 409)
        login(True)
        p = next(
            p for p in client.get("/api/bootstrap").json()["products"] if p["id"] == c["preferred"]
        )
        p["stock"] = 0
        assert client.put("/api/admin/products/" + p["id"], json=p).status_code == 200
        login()
        act(c, "sale", {"confirmed_total": quote(c)["total"]}, 409)
        record(
            "stock disappearance blocks sale",
            dict(lines=fresh(c)["flow"]["lines"], sale=fresh(c)["sale"]),
        )
        # IST date boundaries: history survives filtering; automated activity is excluded.
        c = new("Returning visitor")
        with store.transaction() as db:
            saved = store.get(db, "customers", c["id"])
            saved["activities"] = ["2026-10-31T18:29:59+00:00", "2026-11-01T18:29:59+00:00"]
            store.put(db, "customers", saved)
        ids = [
            x["id"]
            for x in client.get("/api/bootstrap?start=2026-11-01&end=2026-11-01").json()[
                "customers"
            ]
        ]
        record(
            "IST inclusive activity filter returning customer",
            dict(
                count=ids.count(c["id"]),
                history_retained=len(fresh(c)["messages"]) == len(c["messages"]),
            ),
        )
        login(True)
        filtered = client.get("/api/bootstrap?associate=associate-2").json()
        record(
            "admin associate scope",
            dict(
                customer_owners=sorted(set(c["owner"] for c in filtered["customers"])),
                task_owners=sorted(set(t["owner"] for t in filtered["tasks"])),
                attempt_owners=sorted(set(a["owner"] for a in filtered["attempts"])),
            ),
        )

Path("output/improvements-review-evidence.json").write_text(
    json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"{len(evidence)} review observations saved to output/improvements-review-evidence.json")
