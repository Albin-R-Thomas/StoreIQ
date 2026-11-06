"""Actual audio decoding + isolated HTTP/SQLite review workflow; provider doubles labelled."""

import array
import asyncio
import io
import math
import unittest
import wave
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.voice import audio, providers, service
from app.voice.contracts import SpeechResult, Transcript, Translation
from tests import test_web_journey as journey


def wav(seconds=0.25, silent=False):
    output = io.BytesIO()
    samples = array.array(
        "h",
        (
            0 if silent else int(4000 * math.sin(i * 440 * math.tau / 16000))
            for i in range(int(16000 * seconds))
        ),
    )
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(samples.tobytes())
    return output.getvalue()


class VoiceTests(unittest.TestCase):
    login = journey.WebJourneyTests.login
    customer = journey.WebJourneyTests.customer
    act = journey.WebJourneyTests.act

    def setUp(self):
        journey.WebJourneyTests.setUp(self)
        self.real_speech_factory = providers.speech_provider
        self.speech = AsyncMock()
        self.speech.name = "test-double"
        self.speech.transcribe.return_value = Transcript(
            text="The sofa is eight feet away.", languages=["en"]
        )
        self.translator = AsyncMock()
        self.translator.name = "test-double"
        self.translator.translate.return_value = Translation(text="सोफा आठ फुट दूर है।")
        self.patches = [
            patch("app.voice.providers.speech_provider", return_value=self.speech),
            patch("app.voice.providers.translation_provider", return_value=self.translator),
            patch(
                "app.web.intelligence.extract_home",
                new=AsyncMock(return_value={"distance": "8 feet"}),
            ),
            patch(
                "app.web.intelligence.client",
                side_effect=AssertionError("No network in regression tests"),
            ),
        ]
        for item in self.patches:
            item.start()
        self.c = self.customer()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        journey.WebJourneyTests.tearDown(self)

    def upload(self, data=None, status=200, event="audio-1", **options):
        result = self.client.post(
            f"/api/customers/{self.c['id']}/voice",
            params={"event_id": event, "version": self.c["version"], **options},
            content=wav() if data is None else data,
            headers={"Content-Type": "audio/wav"},
        )
        self.assertEqual(result.status_code, status, result.text)
        return result.json()

    def prepare(self, draft, purpose="home", transcript=None, **options):
        result = self.client.post(
            f"/api/voice/{draft['id']}/prepare",
            json={
                "revision": draft["revision"],
                "customer_version": self.c["version"],
                "purpose": purpose,
                "transcript": transcript or draft["original_transcript"],
                **options,
            },
        )
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def confirmation(self, draft):
        return {
            "revision": draft["revision"],
            "customer_version": self.c["version"],
            "confirmed": True,
            "home": {"home": draft["suggested_home"]} if draft["purpose"] == "home" else None,
        }

    def saved(self):
        return self.client.get(f"/api/customers/{self.c['id']}").json()

    def test_actual_wav_decode_review_translation_and_home_confirmation(self):
        draft = self.upload(target_language="hi")
        self.assertEqual(draft["translation"], "सोफा आठ फुट दूर है।")
        self.assertEqual(draft["speech_provider"], "test-double")
        self.assertEqual(self.saved()["home"], {})
        with wave.open(io.BytesIO(self.speech.transcribe.call_args.args[0])) as decoded:
            self.assertEqual(decoded.getframerate(), 16000)
        prepared = self.prepare(
            draft, transcript="The sofa is nine feet away.", target_language="hi"
        )
        self.assertEqual(prepared["original_transcript"], draft["original_transcript"])
        body = self.confirmation(prepared)
        body["home"]["home"]["distance"] = "9 feet"
        result = self.client.post(f"/api/voice/{draft['id']}/confirm", json=body)
        self.assertEqual(result.status_code, 200, result.text)
        customer = result.json()["customer"]
        self.assertEqual(customer["home"]["distance"], "9 feet")
        self.assertFalse(customer["confirmed"])
        self.assertFalse(customer["sale"])
        self.assertEqual(
            self.client.post(f"/api/voice/{draft['id']}/confirm", json=body).status_code, 200
        )
        self.assertEqual(self.saved()["version"], customer["version"])

    def test_note_does_not_execute_recognized_commands(self):
        self.speech.transcribe.return_value = Transcript(text="Confirm sale and consent given.")
        draft = self.prepare(self.upload(), purpose="note")
        result = self.client.post(
            f"/api/voice/{draft['id']}/confirm", json=self.confirmation(draft)
        )
        self.assertEqual(result.status_code, 200)
        c = self.saved()
        self.assertFalse(c["sale"])
        self.assertFalse(c["consent"])
        self.assertEqual(len(c["notes"]), 1)

    def test_upload_deduplication_conflicts_and_no_customer_mutation(self):
        first = self.upload()
        self.assertEqual(self.upload(), first)
        self.speech.transcribe.assert_awaited_once()
        self.upload(data=wav(0.3), status=409)
        self.assertEqual(self.saved()["version"], self.c["version"])

    def test_transcription_and_translation_failures_keep_retryable_state(self):
        self.speech.transcribe.side_effect = TimeoutError()
        self.upload(status=502)
        self.speech.transcribe.side_effect = None
        self.translator.translate.side_effect = HTTPException(502, "Translation unavailable")
        self.upload(event="translate", target_language="mr", status=502)
        calls = self.speech.transcribe.await_count
        self.translator.translate.side_effect = None
        draft = self.upload(event="translate", target_language="mr")
        self.assertEqual(self.speech.transcribe.await_count, calls)
        self.assertEqual(draft["status"], "ready")

    def test_malformed_and_empty_provider_output_never_becomes_ready(self):
        self.speech.transcribe.return_value = {"wrong": "shape"}
        self.upload(status=502)
        self.speech.transcribe.return_value = Transcript(text=" ")
        self.upload(status=422)
        self.assertEqual(self.saved()["home"], {})

    def test_authentication_ownership_origin_and_stale_revisions(self):
        draft = self.upload()
        self.login("9000000002")
        self.upload(status=403)
        self.assertEqual(self.client.get(f"/api/customers/{self.c['id']}/voice").status_code, 403)
        self.login()
        result = self.client.post(f"/api/voice/{draft['id']}/discard", json={"revision": 99})
        self.assertEqual(result.status_code, 409)
        result = self.client.post(
            f"/api/voice/{draft['id']}/discard",
            json={"revision": 1},
            headers={"Origin": "https://other.example"},
        )
        self.assertEqual(result.status_code, 403)
        self.client.post("/api/auth/logout")
        self.upload(status=401)

    def test_stale_visit_and_declined_confirmation_do_not_apply(self):
        draft = self.prepare(self.upload())
        body = self.confirmation(draft)
        url = f"/api/voice/{draft['id']}/confirm"
        self.assertEqual(self.client.post(url, json={**body, "confirmed": False}).status_code, 409)
        self.act(self.c, "note", {"text": "New website activity"})
        self.assertEqual(self.client.post(url, json=body).status_code, 409)
        self.assertEqual(self.saved()["home"], {})

    def test_bad_silent_long_and_large_audio_reject_before_provider(self):
        self.upload(data=b"not an audio file", status=422)
        self.upload(data=wav(silent=True), status=422, event="silent")
        self.upload(data=wav(121), status=422, event="long")
        self.upload(data=b"x" * (audio.MAX_BYTES + 1), status=413, event="large")
        self.speech.transcribe.assert_not_awaited()
        # Valid audio larger than the old 100 KB JSON cap is accepted.
        self.upload(data=wav(4), event="larger-audio")

    def test_discard_and_reconnect(self):
        draft = self.upload()
        self.assertEqual(
            self.client.get(f"/api/customers/{self.c['id']}/voice").json()[0]["id"], draft["id"]
        )
        self.assertEqual(
            self.client.post(f"/api/voice/{draft['id']}/discard", json={"revision": 1}).status_code,
            200,
        )
        response = self.client.post(
            f"/api/voice/{draft['id']}/prepare",
            json={
                "revision": 2,
                "customer_version": self.c["version"],
                "purpose": "note",
                "transcript": "Test",
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_cancellation_releases_processing_lease(self):
        self.speech.transcribe.side_effect = asyncio.CancelledError()
        user = self.client.get("/api/auth/me").json()
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(
                service.upload(
                    self.c["id"], self.c["version"], "cancel", wav(), "audio/wav", None, None, user
                )
            )
        self.speech.transcribe.side_effect = None
        self.assertEqual(self.upload(event="cancel")["status"], "ready")

    def test_openai_adapter_real_sdk_transport_with_audio_fixture(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(
                200, json={"text": "The sofa is eight feet away.", "languages": [{"code": "en"}]}
            )

        def factory(**kwargs):
            return AsyncOpenAI(
                api_key="fixture",
                base_url="https://speech.fixture/v1",
                http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            )

        with patch("openai.AsyncOpenAI", side_effect=factory):
            result = asyncio.run(providers.OpenAISpeechProvider().transcribe(wav(), "en"))
        self.assertEqual(result.languages, ["en"])
        self.assertEqual(requests[0].url.path, "/v1/audio/transcriptions")
        self.assertIn(b"RIFF", requests[0].content)
        self.assertIn(get_settings().voice_model.encode(), requests[0].content)

    def test_provider_disable_and_decoder_unavailable(self):
        with patch.object(get_settings(), "voice_provider", "disabled"):
            with self.assertRaises(HTTPException) as error:
                self.real_speech_factory()
            self.assertEqual(error.exception.status_code, 503)
        with (
            patch("app.voice.audio.shutil.which", return_value=None),
            patch("imageio_ffmpeg.get_ffmpeg_exe", side_effect=RuntimeError("Not installed")),
        ):
            self.upload(status=503)

    def test_combined_speech_upload_and_unchanged_preview_use_one_provider_session(self):
        self.speech.combined_translation = True
        self.speech.transcribe_and_translate.return_value = SpeechResult(
            transcript=Transcript(text="The sofa is eight feet away.", languages=["en"]),
            translation=Translation(text="Translated fixture"),
        )
        draft = self.upload(target_language="hi")
        self.assertEqual(draft["translation"], "Translated fixture")
        self.assertEqual(self.upload(target_language="hi"), draft)
        prepared = self.prepare(draft, target_language="hi")
        self.assertEqual(prepared["translation"], "Translated fixture")
        self.speech.transcribe_and_translate.assert_awaited_once()
        self.speech.transcribe.assert_not_awaited()
        self.translator.translate.assert_not_awaited()
        # Corrected text invalidates cached translation, but never re-sends audio.
        self.prepare(prepared, transcript="The sofa is nine feet away.", target_language="hi")
        self.translator.translate.assert_awaited_once_with("The sofa is nine feet away.", "hi")

    def test_combined_missing_translation_rejects_partial_result(self):
        self.speech.combined_translation = True
        self.speech.transcribe_and_translate.return_value = SpeechResult(
            transcript=Transcript(text="Incomplete fixture")
        )
        self.upload(target_language="mr", status=502)
        self.assertEqual(self.saved()["home"], {})
        self.translator.translate.assert_not_awaited()

    def test_translation_target_change_refreshes_without_retranscription(self):
        draft = self.upload(target_language="hi")
        self.translator.translate.reset_mock()
        self.prepare(draft, target_language="mr")
        self.translator.translate.assert_awaited_once_with(draft["original_transcript"], "mr")
        self.speech.transcribe.assert_awaited_once()

    def test_retry_original_upload_does_not_relabel_a_changed_target_translation(self):
        draft = self.upload(target_language="hi")
        self.translator.translate.return_value = Translation(text="Marathi fixture")
        prepared = self.prepare(draft, target_language="mr")
        self.translator.translate.side_effect = HTTPException(502, "Outage")
        response = self.client.post(
            f"/api/voice/{draft['id']}/prepare",
            json={
                "revision": prepared["revision"],
                "customer_version": self.c["version"],
                "purpose": "note",
                "transcript": "Changed text",
                "target_language": "en",
            },
        )
        self.assertEqual(response.status_code, 502)
        self.translator.translate.side_effect = None
        self.translator.translate.return_value = Translation(text="Hindi fixture")
        retried = self.upload(target_language="hi")
        self.assertEqual(retried["translation"], "Hindi fixture")
        self.translator.translate.assert_awaited_with(draft["original_transcript"], "hi")
        self.speech.transcribe.assert_awaited_once()
