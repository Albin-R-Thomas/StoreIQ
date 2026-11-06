"""Azure adapters. Initial audio translation uses one Speech SDK session."""

import asyncio
import base64
import json
import subprocess
import sys

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import get_settings
from app.voice.contracts import Language, SpeechResult, Transcript, Translation


class AzureSpeechProvider:
    name = "azure"
    combined_translation = True

    async def transcribe(self, wav: bytes, language: Language | None) -> Transcript:
        return (await self.transcribe_and_translate(wav, language, None)).transcript

    async def transcribe_and_translate(
        self, wav: bytes, language: Language | None, target: Language | None
    ) -> SpeechResult:
        settings = get_settings()
        key = settings.azure_speech_key.get_secret_value()
        region = settings.azure_speech_region.strip()
        if not key or not region:
            raise HTTPException(503, "Configure AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.")
        # Isolate the native SDK so cancellation/timeout can stop network work,
        # including a hung native start/stop. Keys/audio travel via stdin, not argv.
        payload = json.dumps({
            "key": key, "region": region, "source": language, "target": target,
            "wav": base64.b64encode(wav).decode("ascii"),
        }).encode()
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "app.voice.azure_worker",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}),
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(payload), timeout=180)
            if process.returncode:
                raise HTTPException(502, "Azure Speech unavailable. Retry or use typed input.")
            result = json.loads(stdout)
            if "error" in result:
                code = result["error"]
                if code == "authentication":
                    raise HTTPException(503, "Azure Speech rejected the key/region configuration.")
                if code == "no_speech":
                    raise HTTPException(422, "No speech recognized; retry or type the details.")
                raise HTTPException(502, "Azure Speech unavailable. Retry or use typed input.")
            parsed = SpeechResult.model_validate(result)
            if not parsed.transcript.text.strip() or (target and parsed.translation is None):
                raise ValueError("Incomplete speech result")
            return parsed
        except (TimeoutError, ValueError, TypeError, ValidationError) as exc:
            raise HTTPException(502, "Azure Speech timed out or returned unreadable output.") from exc
        finally:
            if process.returncode is None:
                process.kill()
                await asyncio.shield(process.wait())


class AzureTranslationProvider:
    """Only used for edited text/changed targets or legacy drafts, never normal Azure upload."""

    name = "azure"

    async def translate(self, text: str, target: Language) -> Translation:
        settings = get_settings()
        key = settings.azure_translator_key.get_secret_value()
        if not key:
            raise HTTPException(
                503, "Refreshing edited text needs AZURE_TRANSLATOR_KEY. "
                "Keep the original translation or select Keep original only."
            )
        headers = {"Ocp-Apim-Subscription-Key": key}
        if settings.azure_translator_region.strip():
            headers["Ocp-Apim-Subscription-Region"] = settings.azure_translator_region.strip()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.cognitive.microsofttranslator.com/translate",
                    params={"api-version": "3.0", "to": target, "textType": "plain"},
                    headers=headers, json=[{"Text": text}],
                )
                response.raise_for_status()
            rows = response.json()
            translated = rows[0]["translations"][0]
            if translated["to"] != target:
                raise ValueError("Wrong target")
            return Translation(text=translated["text"])
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise HTTPException(503, "Azure Translator rejected the key/region configuration.") from exc
            raise HTTPException(502, "Azure Translator unavailable or quota exhausted. Retry later.") from exc
        except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(502, "Azure Translator unavailable or returned unreadable output.") from exc
