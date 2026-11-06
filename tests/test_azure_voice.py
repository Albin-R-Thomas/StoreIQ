"""Azure boundary tests: SDK callbacks and HTTP fixtures, not live recognition evidence."""

import asyncio
import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import azure.cognitiveservices.speech as sdk
import httpx
from fastapi import HTTPException
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.voice import azure, azure_worker, providers
from tests.test_voice import wav


class AzureVoiceTests(unittest.TestCase):
    def test_defaults_and_missing_credentials_fail_without_network(self):
        settings = Settings(
            _env_file=None,
            azure_speech_key="",
            azure_speech_region="",
            azure_translator_key="",
            azure_translator_region="",
        )
        with patch("app.voice.providers.get_settings", return_value=settings):
            self.assertIsInstance(providers.speech_provider(), azure.AzureSpeechProvider)
            self.assertIsInstance(providers.translation_provider(), azure.AzureTranslationProvider)
        with patch("app.voice.azure.get_settings", return_value=settings):
            for call in (
                azure.AzureSpeechProvider().transcribe(wav(), None),
                azure.AzureTranslationProvider().translate("Test", "hi"),
            ):
                with self.assertRaises(HTTPException) as error:
                    asyncio.run(call)
                self.assertEqual(error.exception.status_code, 503)

    def worker(self, source=None, target="hi", failure=None, empty=False):
        recognizer = MagicMock()
        stream = MagicMock()
        callbacks = {}
        for event in ("recognized", "canceled", "session_stopped"):
            getattr(recognizer, event).connect.side_effect = lambda callback, name=event: (
                callbacks.update({name: callback})
            )
        active = False

        def finish():
            nonlocal active
            if not active:
                return
            active = False
            if failure:
                callbacks["canceled"](
                    SimpleNamespace(
                        cancellation_details=SimpleNamespace(
                            reason=sdk.CancellationReason.Error,
                            error_code=failure,
                        ),
                    )
                )
            else:
                if not empty:
                    for text in ("First sentence.", "Second sentence."):
                        callbacks["recognized"](
                            SimpleNamespace(
                                result=SimpleNamespace(
                                    reason=(
                                        sdk.ResultReason.TranslatedSpeech
                                        if target and source != target
                                        else sdk.ResultReason.RecognizedSpeech
                                    ),
                                    text=text,
                                    translations={target: "Translation " + text},
                                )
                            )
                        )
                callbacks["session_stopped"](None)

        def start():
            nonlocal active
            active = True

        recognizer.start_continuous_recognition_async.return_value.get.side_effect = start
        stream.close.side_effect = finish
        with (
            patch.object(sdk.audio, "PushAudioInputStream", return_value=stream),
            patch.object(sdk.audio, "AudioConfig") as audio_config,
            patch.object(sdk, "SpeechRecognizer", return_value=recognizer) as speech,
            patch.object(
                sdk.translation, "TranslationRecognizer", return_value=recognizer
            ) as translation,
            patch.object(
                sdk,
                "AutoDetectSourceLanguageResult",
                return_value=SimpleNamespace(language="en-IN"),
            ),
        ):
            result = azure_worker.recognize(
                {
                    "key": "fixture",
                    "region": "centralindia",
                    "source": source,
                    "target": target,
                    "wav": base64.b64encode(wav()).decode(),
                },
                sdk,
            )
        self.assertEqual(speech.call_count + translation.call_count, 1)
        audio_config.assert_called_once_with(stream=stream)
        self.assertFalse(stream.write.call_args.args[0].startswith(b"RIFF"))
        recognizer.stop_continuous_recognition_async.assert_called_once()
        return result

    def test_continuous_results_preserve_all_segments_and_translation(self):
        result = self.worker()
        self.assertEqual(result["transcript"]["text"], "First sentence. Second sentence.")
        self.assertEqual(result["transcript"]["languages"], ["en"])
        self.assertIn("Second sentence.", result["translation"]["text"])

    def test_same_language_and_transcription_only(self):
        result = self.worker(source="hi", target="hi")
        self.assertEqual(result["translation"]["text"], result["transcript"]["text"])
        self.assertIsNone(self.worker(source="mr", target=None)["translation"])

    def test_sdk_cancellation_and_empty_audio_do_not_return_partial_success(self):
        self.assertEqual(
            self.worker(failure=sdk.CancellationErrorCode.AuthenticationFailure),
            {"error": "authentication"},
        )
        self.assertEqual(self.worker(empty=True), {"error": "no_speech"})
        self.assertEqual(
            self.worker(target=None, failure=sdk.CancellationErrorCode.AuthenticationFailure),
            {"error": "authentication"},
        )

    def test_real_sdk_accepts_pcm_and_auto_language_configuration_without_network(self):
        config = sdk.translation.SpeechTranslationConfig(
            subscription="fixture", region="centralindia"
        )
        config.add_target_language("hi")
        stream = sdk.audio.PushAudioInputStream(
            stream_format=sdk.audio.AudioStreamFormat(
                samples_per_second=16000, bits_per_sample=16, channels=1
            )
        )
        recognizer = sdk.translation.TranslationRecognizer(
            translation_config=config,
            auto_detect_source_language_config=sdk.languageconfig.AutoDetectSourceLanguageConfig(
                languages=list(azure_worker.LOCALES.values())
            ),
            audio_config=sdk.audio.AudioConfig(stream=stream),
        )
        self.assertIsNotNone(recognizer)
        stream.close()

    def test_worker_timeout_and_cancellation_kill_native_process(self):
        for exception in (TimeoutError(), asyncio.CancelledError()):
            process = SimpleNamespace(
                communicate=AsyncMock(side_effect=exception),
                returncode=None,
                kill=MagicMock(),
                wait=AsyncMock(return_value=-1),
            )
            with (
                patch.object(get_settings(), "azure_speech_key", SecretStr("fixture")),
                patch.object(get_settings(), "azure_speech_region", "centralindia"),
                patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)),
            ):
                with self.assertRaises(
                    HTTPException if isinstance(exception, TimeoutError) else asyncio.CancelledError
                ):
                    asyncio.run(azure.AzureSpeechProvider().transcribe(wav(), "en"))
            process.kill.assert_called_once()
            process.wait.assert_awaited_once()

    def test_malformed_worker_output_and_auth_errors(self):
        for value, status in (
            (b"not json", 502),
            (b'{"error":"authentication"}', 503),
            (b'{"transcript":{"text":"hello"}}', 502),
        ):
            process = SimpleNamespace(
                communicate=AsyncMock(return_value=(value, b"")), returncode=0
            )
            with (
                patch.object(get_settings(), "azure_speech_key", SecretStr("fixture")),
                patch.object(get_settings(), "azure_speech_region", "centralindia"),
                patch(
                    "asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)
                ) as launch,
            ):
                with self.assertRaises(HTTPException) as error:
                    asyncio.run(
                        azure.AzureSpeechProvider().transcribe_and_translate(wav(), "en", "hi")
                    )
                self.assertEqual(error.exception.status_code, status)
                self.assertNotIn("fixture", str(launch.call_args))

    def test_translator_http_contract_and_failures(self):
        real_client = httpx.AsyncClient
        requests = []
        scenarios = [
            (200, [{"translations": [{"text": "नमस्ते", "to": "hi"}]}], None),
            (401, {"error": "fixture"}, 503),
            (403, {}, 503),
            (429, {}, 502),
            (503, {}, 502),
            (200, [], 502),
            (200, [{"translations": [{"text": " ", "to": "hi"}]}], 502),
            (200, [{"translations": [{"text": "wrong language", "to": "mr"}]}], 502),
        ]
        for status, body, expected in scenarios:

            def handler(request):
                requests.append(request)
                return httpx.Response(status, json=body)

            with (
                patch.object(get_settings(), "azure_translator_key", SecretStr("fixture")),
                patch.object(get_settings(), "azure_translator_region", "centralindia"),
                patch(
                    "app.voice.azure.httpx.AsyncClient",
                    side_effect=lambda **kw: real_client(
                        transport=httpx.MockTransport(handler), **kw
                    ),
                ),
            ):
                call = azure.AzureTranslationProvider().translate("Hello", "hi")
                if expected:
                    with self.assertRaises(HTTPException) as error:
                        asyncio.run(call)
                    self.assertEqual(error.exception.status_code, expected)
                else:
                    self.assertEqual(asyncio.run(call).text, "नमस्ते")
        request = requests[0]
        self.assertEqual(request.url.params["to"], "hi")
        self.assertEqual(request.url.params["api-version"], "3.0")
        self.assertEqual(request.headers["Ocp-Apim-Subscription-Region"], "centralindia")
        self.assertEqual(json.loads(request.content), [{"Text": "Hello"}])
