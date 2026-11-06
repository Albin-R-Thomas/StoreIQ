"""Opt-in synthetic Marathi recording through the existing live voice API."""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import azure.cognitiveservices.speech as sdk
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.web import store

if "--live" not in sys.argv:
    raise SystemExit("Use --live to authorize synthetic speech and recognition provider calls.")

out = Path("output/text-final-acceptance-2026-11-06")
out.mkdir(parents=True, exist_ok=True)
settings = get_settings()
config = sdk.SpeechConfig(
    subscription=settings.azure_speech_key.get_secret_value(),
    region=settings.azure_speech_region,
)
synth = sdk.SpeechSynthesizer(speech_config=config, audio_config=None)
voices = synth.get_voices_async("mr-IN").get()
assert voices.voices, "No Marathi test voice available on the configured resource"
config.speech_synthesis_voice_name = voices.voices[0].short_name
config.set_speech_synthesis_output_format(sdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)
synth = sdk.SpeechSynthesizer(speech_config=config, audio_config=None)
spoken = "ग्राहकाला क्रिकेट आणि चित्रपट पाहण्यासाठी टीव्ही हवा आहे. सोफा टीव्हीपासून नऊ फूट दूर आहे. खोलीत भरपूर सूर्यप्रकाश येतो."
recording = synth.speak_text_async(spoken).get()
assert recording.reason == sdk.ResultReason.SynthesizingAudioCompleted, "Synthetic recording failed"
(out / "synthetic-marathi.wav").write_bytes(recording.audio_data)
results = []
with (
    tempfile.TemporaryDirectory() as directory,
    patch.object(store, "DB_PATH", Path(directory) / "voice.db"),
    TestClient(create_app()) as client,
):
    assert (
        client.post(
            "/api/auth/login", json={"phone": "9000000001", "password": "Associate@123"}
        ).status_code
        == 200
    )
    c = client.post("/api/customers", json={"name": "Synthetic Marathi voice acceptance"}).json()
    for source, target in [("auto", "en"), ("mr", "mr")]:
        start = time.perf_counter()
        response = client.post(
            f"/api/customers/{c['id']}/voice",
            params={
                "version": c["version"],
                "event_id": "marathi-" + target,
                "source_language": source,
                "target_language": target,
            },
            content=recording.audio_data,
            headers={"Content-Type": "audio/wav"},
        )
        draft = response.json()
        result = {
            "source": source,
            "target": target,
            "status": response.status_code,
            "seconds": round(time.perf_counter() - start, 3),
            "draft": draft,
        }
        results.append(result)
        (out / "marathi-voice.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        assert response.status_code == 200, draft
        assert draft["translation"] and draft["original_transcript"]
        if target == "en":
            assert "cricket" in draft["translation"].casefold(), draft["translation"]
        else:
            assert "क्रिकेट" in draft["translation"], draft["translation"]
        assert client.get(f"/api/customers/{c['id']}").json()["home"] == {}
print(
    "Live synthetic Marathi recognition: auto->English and Marathi->Marathi passed; visit unchanged."
)
