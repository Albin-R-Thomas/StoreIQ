"""Regression evidence for corrected transitions in the documented web journey."""

import unittest
from datetime import UTC, datetime, timedelta

from app.web import api, domain, store
from tests import test_web_journey as journey


class ImprovementTests(unittest.TestCase):
    setUp = journey.WebJourneyTests.setUp
    tearDown = journey.WebJourneyTests.tearDown
    login = journey.WebJourneyTests.login
    customer = journey.WebJourneyTests.customer
    act = journey.WebJourneyTests.act
    ready_customer = journey.WebJourneyTests.ready_customer

    def text(self, c, text):
        r = self.client.post(f"/api/customers/{c['id']}/messages", json={"text": text})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_single_match_demo_and_home_site_invalidation(self):
        c = self.ready_customer()
        c = self.act(c, "home", {"home": {"budget": "30000", "placement": "Table"}})
        self.assertFalse(c["site"].get("confirmed"))
        c = self.act(c, "confirm_home")
        self.assertEqual(len(c["selected"]), 1)
        self.assertIn("Demo TV", [b["label"] for b in c["flow"]["buttons"]])
        c = self.act(c, "start_demo")
        c = self.act(
            c,
            "demo",
            {
                "preferred": c["selected"][0],
                "reason": "Customer liked the picture after physical demo",
            },
        )
        self.assertEqual(c["demo"]["kind"], "single TV")
        self.assertIsNone(c["flow"]["quote"]["total"])

    def test_site_individual_checks_unknown_and_old_note_rejected(self):
        c = self.ready_customer()
        self.act(c, "site", {"placement": "Wall", "specialist": "no", "notes": "maybe"}, 422)
        c = self.act(
            c,
            "site",
            {
                "placement": "Wall",
                "specialist": "unknown",
                "notes": "Awaiting site inspection",
                "power": "Checked",
                "cable_route": "Unknown",
                "access": "Checked",
                "devices": "Checked",
            },
        )
        self.assertFalse(c["site"]["confirmed"])
        self.assertIsNone(c["flow"]["quote"]["total"])
        self.act(c, "payment", {"method": "full"}, 409)

    def preview_share(self, c):
        c = self.act(c, "consent", {"given": True})
        body = {
            "version": c["version"],
            "action": "preview",
            "data": {"recipient": "Synthetic test recipient"},
        }
        r = self.client.post(f"/api/customers/{c['id']}/share-preview", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        return c, r.json()

    def test_commercial_staleness_and_preview_bound_to_dependencies(self):
        c, preview = self.preview_share(self.ready_customer())
        path = f"/api/customers/{c['id']}/share"
        body = {
            "version": c["version"],
            "action": "share",
            "data": {"confirmed": True, "preview_id": preview["id"]},
        }
        created = self.client.post(path, json=body)
        self.assertEqual(created.status_code, 201, created.text)
        token = created.json()["path"].split("/")[-1]
        self.assertEqual(self.client.post(path, json=body).status_code, 409)
        with store.transaction() as db:
            p = store.get(db, "products", c["preferred"])
            p["price"] += 1234
            store.put(db, "products", p)
        self.assertTrue(self.client.get("/api/shared/" + token).json()["outdated"])
        c, preview = self.preview_share(c)
        with store.transaction() as db:
            terms = store.get(db, "commercial", "terms")
            terms["delivery"] += 1
            store.put(db, "commercial", terms)
        body.update(version=c["version"], data={"confirmed": True, "preview_id": preview["id"]})
        self.assertEqual(self.client.post(path, json=body).status_code, 409)

    def test_resolved_blocker_requires_evidence_and_same_thread_reopens(self):
        c = self.ready_customer()
        payload = {
            "customer_id": c["id"],
            "question": "Confirm device compatibility",
            "blocking": True,
        }
        r = self.client.post("/api/requests", json=payload).json()
        self.client.post(
            f"/api/requests/{r['id']}/action", json={"version": 1, "action": "resolve"}
        )
        c = self.client.get("/api/customers/" + c["id"]).json()
        self.act(c, "payment", {"method": "full"}, 409)
        self.client.post(
            f"/api/requests/{r['id']}/action",
            json={
                "version": 1,
                "action": "resolve",
                "data": {
                    "evidence": "Verified HDMI input against approved device manual; use HDMI 1."
                },
            },
        )
        c = self.client.get("/api/customers/" + c["id"]).json()
        c = self.act(c, "payment", {"method": "full"})
        reopened = self.client.post("/api/requests", json=payload).json()
        self.assertEqual(r["id"], reopened["id"])
        self.assertEqual(reopened["status"], "waiting")
        c = self.client.get("/api/customers/" + c["id"]).json()
        self.act(c, "sale", {"confirmed_total": c["flow"]["quote"]["total"]}, 409)

    def test_task_reopening_invalidates_dependents_and_closure(self):
        c = self.act(self.ready_customer(), "payment", {"method": "full"})
        c = self.act(c, "sale", {"confirmed_total": c["flow"]["quote"]["total"]})
        tasks = {t["kind"]: t for t in self.client.get("/api/bootstrap").json()["tasks"]}
        body = {
            "status": "completed",
            "detail": "Confirmed picture, sound, devices and satisfaction",
            "assigned_to": "Test owner",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        }
        for kind in ["delivery", "installation", "working_check"]:
            self.assertEqual(
                self.client.post("/api/tasks/" + tasks[kind]["id"], json=body).status_code, 200
            )
        for status in ["pending", "confirmed", "problem"]:
            body["status"] = status
            self.assertEqual(
                self.client.post(
                    "/api/tasks/" + tasks["installation"]["id"], json=body
                ).status_code,
                200,
            )
            current = self.client.get("/api/customers/" + c["id"]).json()
            self.assertEqual(current["stage"], "handover")
        check = next(
            t
            for t in self.client.get("/api/bootstrap").json()["tasks"]
            if t["kind"] == "working_check"
        )
        self.assertEqual(check["status"], "pending")

    def test_scheduler_due_tasks_notify_once_and_reschedule(self):
        c = self.customer()
        with store.transaction() as db:
            task = domain.new_task(
                db,
                c,
                "followup",
                "Test owner",
                (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
                "Internal status check",
                False,
            )
            api.reminder_cycle(db)
            api.reminder_cycle(db)
            notes = store.read_all(db, "notifications")
            self.assertEqual(len(notes), 1)
            self.assertIn("internal", notes[0]["title"])
            task = store.get(db, "tasks", task["id"])
            task["due_at"] = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
            store.put(db, "tasks", task)
            api.reminder_cycle(db)
            self.assertEqual(len(store.read_all(db, "notifications")), 2)

    def test_price_dates_preferences_and_training_resume(self):
        c = self.customer()
        c = self.text(c, "What is the current price of Samsung Vision Q55?")
        self.assertTrue(any("64,990" in m["text"] for m in c["messages"]))
        c = self.text(c, "Change options to a smaller size from another brand")
        self.assertEqual(c["preferences"]["exclude_brand"], "Samsung")
        self.assertEqual(c["preferences"]["max_size"], 54)
        c = self.text(c, "Customers from 5 Nov 2026 to 1 Nov 2026")
        self.assertIn("valid date range", c["messages"][-1]["text"])
        bootstrap = self.client.get("/api/bootstrap").json()
        q = bootstrap["questions"][0]
        self.client.post("/api/training", json={"question_id": q["id"], "choice": 0})
        state = self.client.get("/api/bootstrap").json()["practice"]
        self.assertEqual(state["answered"], [q["id"]])
        self.assertIsNotNone(state["feedback"])
        self.client.post("/api/training/session", json={"action": "finish", "version": 1})
        self.assertTrue(self.client.get("/api/bootstrap").json()["practice"]["finished"])
        self.client.post("/api/training/session", json={"action": "repeat", "version": 1})
        self.assertEqual(self.client.get("/api/bootstrap").json()["practice"]["answered"], [])

    def test_filtered_queue_and_partial_scoring(self):
        c = self.ready_customer()
        self.act(
            c,
            "followup",
            {
                "consent": False,
                "reason": "Pending decision",
                "owner": "Test owner",
                "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            },
        )
        self.login("9000000009", "Admin@123")
        filtered = self.client.get("/api/bootstrap?associate=associate-2").json()
        self.assertTrue(all(v["owner"] == "associate-2" for v in filtered["customers"]))
        self.assertTrue(
            all(v["customer_id"] != c["id"] for v in filtered["tasks"] + filtered["requests"])
        )
        self.assertTrue(all(v["owner"] == "associate-2" for v in filtered["attempts"]))
        empty = self.client.get("/api/bootstrap?start=2000-01-01&end=2000-01-02").json()
        self.assertEqual(empty["tasks"], [])
        c["confirmed"] = False
        scores = domain.score(c, [])
        assess = next(s for s in scores if s["step"] == "Assess")
        self.assertEqual(assess["points"], 1)
        self.assertLess(sum(s["applicable"] for s in scores), 7)

    def test_written_languages_preserve_cost_and_action_identifiers(self):
        c = self.ready_customer()
        amount = f"{c['flow']['quote']['total']:,}"
        for language, fragment in [("Hindi", "लागत"), ("Marathi", "किंमत")]:
            c = self.act(c, "language", {"language": language})
            text = " ".join(c["flow"]["lines"])
            self.assertIn(fragment, text)
            self.assertIn(amount, text)
            self.assertEqual(
                [b["name"] for b in c["flow"]["buttons"]], ["extras", "site", "offers"]
            )
        c = self.act(c, "language", {"language": "English"})
        self.assertEqual(c["flow"]["buttons"][0]["label"], "Optional extras")
