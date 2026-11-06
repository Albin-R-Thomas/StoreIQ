"""Opt-in live voice check using a supplied SYNTHETIC recording and isolated database."""

import argparse
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.web import store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="Make paid configured-provider calls")
    parser.add_argument("--content-type", default="audio/wav")
    parser.add_argument("--speech-only", action="store_true",
                        help="Save an unchanged note; needs only Speech credentials")
    parser.add_argument("--source", choices=["auto", "en", "hi", "mr"], default="en")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to authorize sending synthetic audio to the configured provider")
    with tempfile.TemporaryDirectory(prefix="storeiq-live-voice-") as directory:
        with (
            patch.object(store, "DB_PATH", Path(directory) / "voice.db"),
            TestClient(create_app()) as client,
        ):

            def checked(response):
                if response.is_error:
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {response.json().get('detail')}"
                    )
                return response.json()

            checked(
                client.post(
                    "/api/auth/login", json={"phone": "9000000001", "password": "Associate@123"}
                )
            )
            customer = checked(
                client.post("/api/customers", json={"name": "Synthetic audio check"})
            )
            started = time.monotonic()
            draft = checked(
                client.post(
                    f"/api/customers/{customer['id']}/voice",
                    params={
                        "event_id": "live-audio",
                        "version": customer["version"],
                        "target_language": "hi",
                        "source_language": args.source,
                    },
                    content=args.audio.read_bytes(),
                    headers={"Content-Type": args.content_type},
                )
            )
            upload_seconds = round(time.monotonic() - started, 2)
            assert checked(client.get(f"/api/customers/{customer['id']}"))["home"] == {}
            prepared = checked(
                client.post(
                    f"/api/voice/{draft['id']}/prepare",
                    json={
                        "revision": draft["revision"],
                        "customer_version": customer["version"],
                        "transcript": draft["original_transcript"],
                        "purpose": "note" if args.speech_only else "home",
                        "target_language": "hi" if args.speech_only else "mr",
                    },
                )
            )
            result = checked(
                client.post(
                    f"/api/voice/{draft['id']}/confirm",
                    json={
                        "revision": prepared["revision"],
                        "customer_version": customer["version"],
                        "confirmed": True,
                        "home": None if args.speech_only else {"home": prepared["suggested_home"]},
                    },
                )
            )
            assert not result["customer"]["confirmed"] and not result["customer"]["sale"]
            print(
                json.dumps(
                    {
                        "transcript": draft["original_transcript"],
                        "hindi": draft["translation"],
                        "review_translation": prepared["translation"],
                        "review_target": prepared["target_language"],
                        "home": result["customer"]["home"],
                        "duration_seconds": draft["duration_seconds"],
                        "upload_seconds": upload_seconds,
                        "speech_provider": draft["speech_provider"],
                        "status": "passed",
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()
