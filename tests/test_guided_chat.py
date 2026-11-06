"""The documented message buttons drive real saved workflows, without a model."""

import unittest
from unittest.mock import patch

from tests import test_web_journey as journey


class GuidedChatTests(unittest.TestCase):
    setUp = journey.WebJourneyTests.setUp
    tearDown = journey.WebJourneyTests.tearDown
    login = journey.WebJourneyTests.login
    customer = journey.WebJourneyTests.customer
    act = journey.WebJourneyTests.act
    ready_customer = journey.WebJourneyTests.ready_customer

    def labels(self, c):
        flow = c["flow"]
        self.assertLessEqual(len(flow["lines"]), 3)
        self.assertLessEqual(len(flow["buttons"]), 3)
        return [b["label"] for b in flow["buttons"]]

    def text(self, c, text, request_id):
        result = self.client.post(
            f"/api/customers/{c['id']}/messages", json={"text": text, "request_id": request_id}
        )
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_home_questions_buttons_and_text_commands_need_no_model(self):
        c = self.customer()
        self.assertEqual(c["flow"]["question"], "distance")
        self.assertIn("Ask customer", self.labels(c))
        with patch(
            "app.web.intelligence.client",
            side_effect=AssertionError("Guided answers must not call AI"),
        ):
            c = self.act(c, "ask_home")
            c = self.text(c, "9 feet", "distance")
            self.assertEqual(c["home"]["distance"], "9 feet")
            self.assertEqual(c["flow"]["question"], "light")
            c = self.act(c, "home_answer", {"field": "light", "value": "Unknown"})
            for field, value in [
                ("use", "Cricket and movies"),
                ("seating", "On the sides"),
                ("problem", "Motion blur"),
                ("placement", "Wall"),
                ("budget", "70000"),
            ]:
                self.assertEqual(c["flow"]["question"], field)
                c = self.act(c, "home_answer", {"field": field, "value": value})
            self.assertEqual(self.labels(c), ["Correct", "Edit", "Ask customer"])
            c = self.text(c, "Correct", "confirm")
            self.assertTrue(c["confirmed"])
            self.assertEqual(self.labels(c), ["Demo A/B", "Change options", "Stock details"])
            c = self.text(c, "Demo A/B", "start-demo")
            self.assertEqual(self.labels(c), ["Demo done", "Need another demo", "Demo unavailable"])
            c = self.text(c, "Demo done", "done-command")
            self.assertIsNone(c["demo"])
            self.assertEqual(c["flow"]["buttons"][0]["kind"], "input")
            self.assertEqual(c["flow"]["buttons"][0]["name"], "demo")

    def test_combined_reply_and_correction_use_extraction(self):
        from unittest.mock import AsyncMock

        c = self.customer()
        c = self.act(c, "ask_home")
        c = self.text(c, "9 feet", "first")
        extract = AsyncMock(return_value={"light": "Sunny", "use": "Netflix", "budget": "70000"})
        with patch("app.web.intelligence.extract_home", extract):
            c = self.text(c, "Sunny, Netflix, around seventy thousand", "combined")
        self.assertEqual(c["home"]["use"], "Netflix")
        self.assertEqual(c["home"]["budget"], "70000")
        with patch(
            "app.web.intelligence.extract_home", AsyncMock(return_value={"distance": "12 feet"})
        ):
            c = self.text(c, "Actually twelve feet", "correction")
        self.assertEqual(c["home"]["distance"], "12 feet")
        self.assertEqual(c["home"]["use"], "Netflix")

    def test_ambiguous_answer_keeps_question_pending(self):
        from unittest.mock import AsyncMock

        c = self.customer()
        with patch("app.web.intelligence.extract_home", AsyncMock(return_value={})):
            c = self.text(c, "2 hand lengths", "vague")
        self.assertNotIn("distance", c["home"])
        self.assertEqual(c["flow"]["question"], "distance")

    def test_extraction_rejects_ambiguous_measurements_and_range(self):
        import asyncio
        from unittest.mock import AsyncMock

        from app.web import intelligence

        value = intelligence.ExtractedHome(
            distance="2 hand lengths",
            light="Sunny",
            use=None,
            seating=None,
            problem=None,
            placement="that thing",
            budget="affordable",
        )
        with patch("app.web.intelligence.structured", AsyncMock(return_value=value)):
            result = asyncio.run(intelligence.extract_home("test", {}, pending="distance"))
        self.assertEqual(result, {"light": "Sunny"})

    def test_full_button_journey_and_explicit_sale_consent(self):
        c = self.ready_customer()
        self.assertEqual(self.labels(c), ["Optional extras", "Site check", "Continue"])
        c = self.act(c, "offers")
        self.assertEqual(self.labels(c), ["Pay in full", "Finance", "Save for later"])
        c = self.act(c, "payment", {"method": "full"})
        self.assertEqual(self.labels(c), ["Confirm sale", "Save for later", "Open summary"])
        self.assertFalse(c["sale"])
        q = c["flow"]["quote"]
        c = self.act(c, "sale", {"confirmed_total": q["total"]})
        self.assertEqual(self.labels(c), ["Consent given", "No consent", "Review details"])
        c = self.act(c, "consent", {"given": False})
        self.assertEqual(self.labels(c), ["Completed", "Problem", "Ask an expert"])
        self.assertFalse(c["consent"])
        self.assertTrue(c["consent_recorded"])
        self.assertTrue(any(m.get("buttons") for m in c["messages"]))

    def test_demo_and_cost_gates_still_apply_to_conversation_buttons(self):
        c = self.customer()
        self.act(c, "offers", status=409)
        self.act(c, "home_answer", {"field": "budget", "value": "70000"}, status=409)
        c = self.ready_customer()
        c = self.act(
            c,
            "site",
            {
                "placement": "Wall",
                "specialist": "yes",
                "power": "Socket checked",
                "cable_route": "Route checked",
                "access": "Access checked",
                "devices": "Devices checked",
                "notes": "Specialist drilling charge is unconfirmed",
            },
        )
        self.act(c, "offers", status=409)
        self.assertEqual(c["stage"], "complete")

    def test_pause_resume_and_expert_interruption_preserve_stage(self):
        c = self.ready_customer()
        original_stage = c["stage"]
        c = self.act(c, "ask_expert")
        self.assertEqual(c["stage"], original_stage)
        self.assertEqual(self.labels(c), ["Resolved", "Ask admin", "Ask follow-up"])
        item = self.client.post(
            "/api/requests",
            json={
                "customer_id": c["id"],
                "question": "Confirm the included cable length",
                "blocking": True,
            },
        ).json()
        c = self.client.get("/api/customers/" + c["id"]).json()
        c = self.act(c, "expert_resolved")
        linked = next(
            r for r in self.client.get("/api/bootstrap").json()["requests"] if r["id"] == item["id"]
        )
        self.assertEqual(linked["status"], "resolved")
        self.assertEqual(c["stage"], original_stage)
        c = self.act(c, "end_visit")
        self.assertEqual(c["stage"], "review")
        c = self.act(c, "continue_flow")
        self.assertEqual(c["stage"], original_stage)
        self.assertEqual(self.labels(c), ["Optional extras", "Site check", "Continue"])

    def test_reading_flow_does_not_complete_any_actions(self):
        c = self.ready_customer()
        before = self.client.get("/api/customers/" + c["id"]).json()
        after = self.client.get("/api/customers/" + c["id"]).json()
        self.assertEqual(before["version"], after["version"])
        self.assertEqual(before["messages"], after["messages"])
        self.assertFalse(after["sale"])


if __name__ == "__main__":
    unittest.main()
