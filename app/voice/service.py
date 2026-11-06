"""Transcribe -> review/translate -> preview -> explicit atomic confirmation."""

import asyncio
import hashlib
import json
import time

from fastapi import HTTPException
from pydantic import ValidationError

from app.voice import audio, providers
from app.voice.contracts import Confirm, Prepare, SpeechResult, Transcript, Translation
from app.web import domain, flow, intelligence
from app.web.actions import validate
from app.web.store import audit, get, now, put, read_all, transaction, uid


def owned(db, voice_id, user):
    draft = domain.owned(db, "voice", voice_id, user)
    domain.owned(db, "customers", draft["customer_id"], user)
    return draft


def editable(draft, revision):
    domain.require(draft["status"] not in ("applied", "discarded"), "This voice draft is closed")
    domain.require(draft["revision"] == revision, "Voice draft changed. Reload before continuing.")
    domain.require(draft.get("lease_until", 0) <= time.time(), "Voice processing is in progress")


def failed(voice_id, attempt):
    with transaction() as db:
        draft = get(db, "voice", voice_id)
        if draft and draft.get("attempt") == attempt:
            draft.update(status="retryable", lease_until=0)
            put(db, "voice", draft)


async def upload(customer_id, version, event_id, content, media_type, source, target, user):
    identity = json.dumps([user["id"], customer_id, event_id])
    voice_id = hashlib.sha256(identity.encode()).hexdigest()
    fingerprint = hashlib.sha256(content).hexdigest()
    request = {
        "hash": fingerprint,
        "media_type": media_type,
        "version": version,
        "source": source,
        "target": target,
    }
    attempt = uid()
    with transaction() as db:
        customer = domain.owned(db, "customers", customer_id, user)
        draft = get(db, "voice", voice_id)
        if draft:
            domain.require(
                draft["request"] == request, "Event ID reused with different audio/options"
            )
            if draft["status"] in ("ready", "prepared", "applied", "discarded"):
                return draft
            domain.require(
                draft.get("lease_until", 0) <= time.time(), "Voice processing is in progress"
            )
        domain.require(customer["version"] == version, "Visit changed. Refresh before uploading.")
        draft = draft or {
            "id": voice_id,
            "owner": user["id"],
            "customer_id": customer_id,
            "request": request,
            "created_at": now(),
            "revision": 1,
            "original_transcript": "",
            "target_language": target,
            "source_language": source,
            "translation": None,
            "suggested_home": {},
        }
        draft.update(status="processing", lease_until=time.time() + 240, attempt=attempt)
        put(db, "voice", draft)
    try:
        if not draft["original_transcript"]:
            wav, duration = await asyncio.to_thread(audio.normalize, content, media_type)
            provider = providers.speech_provider()
            combined = None
            if getattr(provider, "combined_translation", False) is True:
                combined = SpeechResult.model_validate(
                    await asyncio.wait_for(
                        provider.transcribe_and_translate(wav, source, target), timeout=185
                    )
                )
                result = combined.transcript
                if target and combined.translation is None:
                    raise HTTPException(502, "Speech provider returned no translation. Retry.")
            else:
                result = Transcript.model_validate(
                    await asyncio.wait_for(provider.transcribe(wav, source), timeout=50)
                )
            if not result.text.strip():
                raise HTTPException(422, "No speech recognized; retry or type the details.")
            with transaction() as db:
                draft = owned(db, voice_id, user)
                domain.require(draft.get("attempt") == attempt, "Voice processing superseded")
                draft.update(
                    original_transcript=result.text,
                    reviewed_transcript=result.text,
                    languages=result.languages,
                    duration_seconds=duration,
                    speech_provider=provider.name,
                )
                if combined and combined.translation:
                    draft.update(
                        translation=combined.translation.text,
                        translation_text=result.text,
                        translation_provider=provider.name,
                    )
                put(db, "voice", draft)
        translated = (
            draft.get("translation")
            if target and draft.get("translation_text") == draft["original_transcript"]
            and draft.get("target_language") == target else None
        )
        if target and translated is None:
            translator = providers.translation_provider()
            translated = Translation.model_validate(
                await asyncio.wait_for(
                    translator.translate(
                        draft["original_transcript"], target
                    ),
                    timeout=40,
                )
            ).text
            draft["translation_provider"] = translator.name
        translation_provider_name = draft.get("translation_provider") if target else None
        with transaction() as db:
            draft = owned(db, voice_id, user)
            domain.require(draft.get("attempt") == attempt, "Voice processing superseded")
            draft.update(
                status="ready", lease_until=0, translation=translated, target_language=target,
                translation_text=draft["original_transcript"] if target else None,
                translation_provider=translation_provider_name,
            )
            put(db, "voice", draft)
            audit(db, user["id"], "voice_transcribed", voice_id)
            return draft
    except BaseException as exc:
        failed(voice_id, attempt)
        if isinstance(exc, (TimeoutError, ValidationError)):
            raise HTTPException(
                502, "Voice service unavailable or unreadable. Retry or use typed input."
            ) from exc
        raise


async def prepare(voice_id, body: Prepare, user):
    if not body.transcript.strip():
        raise HTTPException(422, "Review a nonempty transcript")
    if body.purpose == "note" and len(body.transcript) > 3000:
        raise HTTPException(422, "Visit notes must be at most 3000 characters")
    attempt = uid()
    with transaction() as db:
        draft = owned(db, voice_id, user)
        editable(draft, body.revision)
        domain.require(bool(draft["original_transcript"]), "Upload and transcribe audio first")
        customer = domain.owned(db, "customers", draft["customer_id"], user)
        domain.require(
            customer["version"] == body.customer_version, "Visit changed. Refresh first."
        )
        draft.update(lease_until=time.time() + 120, attempt=attempt)
        put(db, "voice", draft)
    try:
        translated = None
        translator_name = None
        if body.target_language:
            if (
                draft.get("translation")
                and draft.get("translation_text") == body.transcript
                and draft.get("target_language") == body.target_language
            ):
                translated = draft["translation"]
                translator_name = draft.get("translation_provider")
            else:
                translator = providers.translation_provider()
                translated = Translation.model_validate(
                    await asyncio.wait_for(
                        translator.translate(body.transcript, body.target_language), timeout=40
                    )
                ).text
                translator_name = translator.name
        home = {}
        if body.purpose == "home":
            home = await asyncio.wait_for(
                intelligence.extract_home(body.transcript, customer["home"], canonical=True),
                timeout=40,
            )
            if not home:
                raise HTTPException(
                    422, "No explicit home details found. Correct the transcript or save a note."
                )
        with transaction() as db:
            draft = owned(db, voice_id, user)
            domain.require(draft.get("attempt") == attempt, "Voice processing superseded")
            draft.update(
                status="prepared",
                lease_until=0,
                revision=draft["revision"] + 1,
                reviewed_transcript=body.transcript,
                translation=translated,
                translation_text=body.transcript if body.target_language else None,
                translation_provider=translator_name,
                target_language=body.target_language,
                purpose=body.purpose,
                suggested_home=home,
                customer_version=body.customer_version,
            )
            put(db, "voice", draft)
            return draft
    except BaseException as exc:
        failed(voice_id, attempt)
        if isinstance(exc, (TimeoutError, ValidationError)):
            raise HTTPException(502, "Voice review unavailable. Retry or use typed input.") from exc
        raise


def confirm(voice_id, body: Confirm, user):
    with transaction() as db:
        draft = owned(db, voice_id, user)
        customer = domain.owned(db, "customers", draft["customer_id"], user)
        if draft["status"] == "applied":
            domain.require(draft["confirmation"] == body.model_dump(), "Confirmation already used")
            return {"voice": draft, "customer": flow.present(db, customer)}
        editable(draft, body.revision)
        domain.require(
            draft["status"] == "prepared" and body.confirmed,
            "Prepare and explicitly confirm the reviewed voice note first",
        )
        domain.require(
            customer["version"] == body.customer_version == draft["customer_version"],
            "Visit changed. Refresh and prepare the voice draft again.",
        )
        if draft["purpose"] == "home":
            domain.require(
                body.home is not None and bool(body.home.home), "Review the proposed home fields"
            )
            values = validate("home", body.home.model_dump())
            action = "home"
        else:
            domain.require(body.home is None, "A visit note cannot update home fields")
            values = validate("note", {"text": draft["reviewed_transcript"]})
            action = "note"
        # Never route recognized speech to command handling: only home or note is allowed.
        domain.message(
            customer,
            "user",
            draft["reviewed_transcript"],
            voice_id=voice_id,
            original_transcript=draft["original_transcript"],
            translation=draft["translation"],
            actor=user["name"],
        )
        domain.act(db, customer, user, action, values)
        flow.append_prompt(db, customer)
        draft.update(
            status="applied",
            confirmation=body.model_dump(),
            applied_at=now(),
            revision=draft["revision"] + 1,
        )
        put(db, "voice", draft)
        audit(db, user["id"], "voice_confirmed", voice_id)
        return {"voice": draft, "customer": flow.present(db, customer)}


def discard(voice_id, revision, user):
    with transaction() as db:
        draft = owned(db, voice_id, user)
        editable(draft, revision)
        draft.update(status="discarded", revision=draft["revision"] + 1)
        put(db, "voice", draft)
        return draft


def drafts(customer_id, user):
    with transaction() as db:
        domain.owned(db, "customers", customer_id, user)
        return [d for d in read_all(db, "voice") if d["customer_id"] == customer_id][-20:]
