"""End-to-end text acceptance: actual saved state, no business-action shortcuts."""

import asyncio
import time
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException

from app.web import domain, message_jobs, store
from tests import test_web_journey as journey


class TextAcceptanceTests(unittest.TestCase):
    setUp = journey.WebJourneyTests.setUp
    tearDown = journey.WebJourneyTests.tearDown
    login = journey.WebJourneyTests.login
    customer = journey.WebJourneyTests.customer

    def send(self, c, text, expected=200, request_id=None):
        r = self.client.post(
            f"/api/customers/{c['id']}/messages",
            json={"text": text, "request_id": request_id or uuid.uuid4().hex},
        )
        while r.status_code == 202:
            time.sleep(0.05)
            r = self.client.get(r.json()["status_url"])
        self.assertEqual(r.status_code, expected, r.text)
        return r.json() if expected == 200 else self.client.get(f"/api/customers/{c['id']}").json()

    def assessed(self):
        c = self.customer()
        with patch(
            "app.web.intelligence.client",
            side_effect=AssertionError("Explicit text must not use AI"),
        ):
            for value in [
                "9 feet",
                "Bright daylight",
                "Cricket and movies",
                "Sides",
                "Motion blur",
                "Wall",
                "70000",
                "Correct",
                "Demo A/B",
                "Demo done",
                "A",
                "Customer prefers the smoother cricket motion",
            ]:
                c = self.send(c, value)
        self.assertIsNotNone(c["demo"])
        return c

    def site_text(self, c, specialist="No"):
        for value in [
            "Site check",
            "Wall",
            "Socket checked",
            "Cable route clear",
            "Wall and lift access checked",
            "Set top box checked",
            specialist,
        ]:
            c = self.send(c, value)
        return c

    def sold(self):
        c = self.site_text(self.assessed())
        c = self.send(c, "Finance")
        c = self.send(c, "Confirm sale")
        self.assertFalse(c["sale"])
        q = self.client.get(f"/api/customers/{c['id']}/summary").json()
        c = self.send(c, f"Confirm {q['finance']['total']}")
        self.assertTrue(c["sale"])
        return c

    def test_text_sale_share_tasks_and_reopening(self):
        c = self.sold()
        c = self.send(c, "No consent")
        c = self.send(c, "Share summary", 409)
        c = self.send(c, "Consent given")
        c = self.send(c, "Share summary")
        c = self.send(c, "Synthetic test recipient")
        self.assertFalse(any(s.get("used") for s in self.records("share_previews")))
        c = self.send(c, "Confirm share")
        shared = next(m["share"] for m in reversed(c["messages"]) if m.get("share"))
        self.assertFalse(
            self.client.get("/api/shared/" + shared["path"].split("/")[-1]).json()["outdated"]
        )
        for kind in ["delivery", "installation", "working check"]:
            for text in [
                kind + " completed",
                "Picture sound devices and satisfaction confirmed",
                "Test owner",
                (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            ]:
                c = self.send(c, text)
        self.assertEqual(c["stage"], "closed")
        for text in [
            "installation problem",
            "Installer is delayed; next update agreed",
            "Installation owner",
            (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        ]:
            c = self.send(c, text)
        self.assertEqual(c["stage"], "handover")
        check = next(
            t
            for t in self.records("tasks")
            if t["customer_id"] == c["id"] and t["kind"] == "working_check"
        )
        self.assertEqual(check["status"], "pending")
        c = self.send(c, "Revoke share")
        self.assertEqual(
            self.client.get("/api/shared/" + shared["path"].split("/")[-1]).status_code, 404
        )

    def records(self, kind):
        with store.transaction() as db:
            return store.read_all(db, kind)

    def test_unknown_specialist_holds_payment_and_cancellable_inputs(self):
        c = self.site_text(self.assessed(), "Unknown")
        self.assertFalse(c["site"]["confirmed"])
        c = self.send(c, "Finance", 409)
        c = self.send(c, "Site check")
        c = self.send(c, "Cancel")
        self.assertNotIn("text_input", c)
        c = self.site_text(c, "Yes")
        self.assertIsNone(self.client.get(f"/api/customers/{c['id']}/summary").json()["total"])
        self.send(c, "Pay in full", 409)

    def test_extras_followup_and_invalid_date_are_text_inputs(self):
        c = self.site_text(self.assessed())
        c = self.send(c, "Add soundbar")
        self.assertEqual(c["extras"], ["soundbar"])
        c = self.send(c, "Remove soundbar")
        c = self.send(c, "Save follow-up")
        for text in [
            "Family decision",
            "No",
            "not a date",
            (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "Aarav owner",
        ]:
            c = self.send(c, text)
        task = next(t for t in self.records("tasks") if t["customer_id"] == c["id"])
        self.assertFalse(task["consent"])
        self.assertEqual(task["assigned_to"], "Aarav owner")

    def test_text_customer_switch_and_conflicting_replay(self):
        target = self.customer()
        original = self.customer()
        c = self.send(original, "All customers")
        c = self.send(c, str(target["serial"]))
        self.assertEqual(c["id"], target["id"])
        c = self.send(c, "Hindi", request_id="same-key")
        self.send(c, "No consent", 409, request_id="same-key")
        c = self.send(c, "New customer Duplicate")
        other = self.send(c, "New customer Duplicate")
        self.assertEqual(other["name"], "Duplicate 2")
        self.assertEqual(other["serial"], c["serial"] + 1)

    def test_unknown_model_and_marathi_next_question_need_no_ai(self):
        c = self.customer()
        with patch("app.web.intelligence.client", side_effect=AssertionError("No provider needed")):
            c = self.send(c, "Explain model XYZ-UNKNOWN-999")
            self.assertIn("Not enough facts present.", c["messages"][-1]["text"])
            c = self.send(c, "Marathi")
            c = self.send(c, "ग्राहकाला क्रिकेटसाठी टीव्ही हवा आहे. कोणता प्रश्न विचारू?")
            self.assertEqual(c["home"]["use"], "Cricket")
            self.assertIn("सोफा", c["messages"][-1]["text"])

    def test_slow_reply_acknowledges_and_exposes_owned_result(self):
        c = self.customer()

        async def slow(*args, **kwargs):
            await asyncio.sleep(1.7)
            return {}

        with patch("app.web.intelligence.extract_home", side_effect=slow):
            start = time.perf_counter()
            r = self.client.post(
                f"/api/customers/{c['id']}/messages",
                json={"text": "unmeasured distance", "request_id": "slow"},
            )
            self.assertEqual(r.status_code, 202, r.text)
            self.assertLess(time.perf_counter() - start, 3)
            url = r.json()["status_url"]
            time.sleep(0.3)
            self.assertEqual(self.client.get(url).status_code, 200)
        self.login("9000000002")
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_slow_provider_error_and_restart_recovery(self):
        c = self.customer()

        async def outage(*args, **kwargs):
            await asyncio.sleep(1.7)
            raise HTTPException(502, "Provider outage")

        with patch("app.web.intelligence.extract_home", side_effect=outage):
            r = self.client.post(
                f"/api/customers/{c['id']}/messages",
                json={"text": "some distance", "request_id": "outage"},
            )
            self.assertEqual(r.status_code, 202)
            time.sleep(0.3)
            failed = self.client.get(r.json()["status_url"])
            self.assertEqual(failed.status_code, 502)
        with store.transaction() as db:
            store.put(
                db,
                "message_jobs",
                dict(
                    id="interrupted",
                    customer_id=c["id"],
                    request_id="restart",
                    owner=c["owner"],
                    status="processing",
                ),
            )
        message_jobs.recover()
        self.assertEqual(
            next(j for j in self.records("message_jobs") if j["id"] == "interrupted")["status"],
            "retryable",
        )

    def test_supported_answer_is_not_full_behavior_evidence(self):
        c = self.customer()
        c["messages"].append(
            dict(role="assistant", coaching_type="validate", sources=[{"id": "guide"}])
        )
        self.assertEqual(
            next(s for s in domain.score(c, []) if s["step"] == "Validate")["points"], 1
        )
        c["coaching_evidence"] = {
            "validate": {"text": "Customer explained resolution versus motion"}
        }
        self.assertEqual(
            next(s for s in domain.score(c, []) if s["step"] == "Validate")["points"], 2
        )

    def test_combined_site_answers_and_uncertain_evidence(self):
        c = self.assessed()
        c = self.send(c, "Site check")
        c = self.send(
            c,
            "Wall, socket checked, cable route clear, lift access checked, set top box checked, no specialist work",
        )
        self.assertTrue(c["site"]["confirmed"])
        c = self.send(c, "Site check")
        c = self.send(
            c,
            "Wall, power not checked yet, cable route clear, lift access checked, set top box checked, no specialist work",
        )
        self.assertFalse(c["site"]["confirmed"])
        self.send(c, "Finance", 409)

    def test_explicit_small_budget_is_never_multiplied(self):
        c = self.customer()
        with store.transaction() as db:
            c["home"]["budget"] = "100 rupees"
            self.assertEqual(domain.recommendations(db, c), [])
            c["home"]["budget"] = "७० हजार"
            self.assertTrue(all(p["price"] <= 70000 for p in domain.recommendations(db, c)))
