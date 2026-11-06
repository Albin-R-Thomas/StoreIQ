"""Bounded native Speech SDK worker; stdout contains only our normalized JSON result."""

import base64
import io
import json
import sys
import threading
import wave

LOCALES = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN"}


def recognize(payload, sdk):
    source, requested_target = payload["source"], payload["target"]
    target = requested_target if requested_target != source else None
    options = {"subscription": payload["key"], "region": payload["region"]}
    config = (
        sdk.translation.SpeechTranslationConfig(**options)
        if target else sdk.SpeechConfig(**options)
    )
    if target:
        config.add_target_language(target)
    kwargs = {}
    if source:
        config.speech_recognition_language = LOCALES[source]
    else:
        kwargs["auto_detect_source_language_config"] = (
            sdk.languageconfig.AutoDetectSourceLanguageConfig(languages=list(LOCALES.values()))
        )
    # At-start language identification is intentional: no claim of mid-sentence
    # code-switch recognition. Use an explicit language for predictable POC results.
    stream = sdk.audio.PushAudioInputStream(
        stream_format=sdk.audio.AudioStreamFormat(
            samples_per_second=16000, bits_per_sample=16, channels=1
        )
    )
    audio_config = sdk.audio.AudioConfig(stream=stream)
    recognizer = (
        sdk.translation.TranslationRecognizer(
            translation_config=config, audio_config=audio_config, **kwargs
        ) if target else sdk.SpeechRecognizer(
            speech_config=config, audio_config=audio_config, **kwargs
        )
    )
    done = threading.Event()
    texts, translations, languages, errors = [], [], [], []

    def recognized(event):
        try:
            result = event.result
            expected = sdk.ResultReason.TranslatedSpeech if target else sdk.ResultReason.RecognizedSpeech
            if not result.text.strip():
                return
            if result.reason != expected:
                errors.append("incomplete_translation")
                return
            texts.append(result.text.strip())
            if target:
                translated = result.translations.get(target, "").strip()
                if not translated:
                    errors.append("incomplete_translation")
                translations.append(translated)
            detected = source or sdk.AutoDetectSourceLanguageResult(result).language
            if detected:
                code = detected.split("-")[0]
                if code not in languages:
                    languages.append(code)
        except Exception:
            errors.append("malformed")
            done.set()

    def canceled(event):
        details = event.cancellation_details
        if details.reason == sdk.CancellationReason.Error:
            errors.append(
                "authentication" if details.error_code == sdk.CancellationErrorCode.AuthenticationFailure
                else "provider"
            )
        done.set()

    recognizer.recognized.connect(recognized)
    recognizer.canceled.connect(canceled)
    recognizer.session_stopped.connect(lambda event: done.set())
    try:
        with wave.open(io.BytesIO(base64.b64decode(payload["wav"])), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
                raise ValueError("Expected normalized PCM")
            pcm = audio.readframes(audio.getnframes())
        recognizer.start_continuous_recognition_async().get()
        stream.write(pcm)
        stream.close()
        if not done.wait(155):
            errors.append("timeout")
    finally:
        stream.close()
        recognizer.stop_continuous_recognition_async().get()
    if errors:
        return {"error": errors[0]}
    if not texts:
        return {"error": "no_speech"}
    return {
        "transcript": {"text": " ".join(texts), "languages": languages},
        "translation": (
            {"text": " ".join(translations) if target else " ".join(texts)}
            if requested_target else None
        ),
    }


def main():
    try:
        import azure.cognitiveservices.speech as sdk

        result = recognize(json.loads(sys.stdin.buffer.read()), sdk)
    except Exception:
        # Never echo SDK diagnostics: they can contain keys, URLs or transcript data.
        result = {"error": "provider"}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
