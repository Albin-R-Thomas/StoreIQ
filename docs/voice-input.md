# Voice transcription, translation and reviewed input (P06)

Implemented 5 November 2026. The website can upload an audio file, transcribe it,
optionally translate the text into English/Hindi/Marathi, and save reviewed home
details or a visit note. This is recorded-file speech-to-text plus text translation;
the chat now captures microphone audio before submitting it for processing. It
does not provide text-to-speech or streaming partial transcription.

## Use it

Open a customer in **Associate chat** and click **Record voice note** beside Send.
Allow microphone access, speak, then click **Stop recording**. Cancel discards the
recording without upload. Recording stops automatically just before two minutes;
the existing server limit remains 120 seconds / 10 MiB. The UI always sends
`source_language=auto` and `target_language=en`. English text is inserted into the
existing message box; existing typed text is preserved. Review/edit it and press
**Send** to use the normal chat flow. Upload alone never sends a chat message or
changes home/sale/consent state. The language selectors, standalone voice panel and
separate voice save controls have been removed from the UI.

On processing failure, the message box is preserved; Retry resends the captured
clip with the same event ID, or Discard removes it. Recording/processing disables
Send. Leaving the customer stops microphone tracks and cancels any browser request.
Tracks also stop immediately on Stop, Cancel or recorder failure. Microphone
permission is enabled only for this site's own origin (`microphone=(self)`), and
requires localhost or HTTPS plus browser consent. The browser selects supported
WebM/Opus, MP4 or OGG/Opus recording. The saved transcript/translation remains in the voice draft store;
the composer text is local and is not restored after reloading. Sent English text
is a normal reviewed chat message, not an applied voice home/note draft.

The dedicated prepare/confirm/discard API described below remains available to API
clients. Those endpoints preserve the separate home/note confirmation workflow.

For the dedicated review API, original and corrected transcripts are preserved separately. Translating or
preparing a draft never completes a demo, sale, consent or task. Recognized speech
is not sent to the general text-command handler by that API: confirmation permits only the
existing `home` or `note` action. The home preview normalizes field values into
English for the current deterministic recommendation rules; the transcript retains
the original language. Translation and extraction need human accuracy review.

## Configuration

```dotenv
VOICE_PROVIDER=azure
VOICE_TRANSLATION_PROVIDER=azure
AZURE_SPEECH_KEY=your-local-speech-secret
AZURE_SPEECH_REGION=your-resource-region
# Optional: only for edited transcripts or a changed translation target.
AZURE_TRANSLATOR_KEY=your-local-translator-secret
AZURE_TRANSLATOR_REGION=your-translator-resource-region
# Existing OpenAI configuration remains necessary for home extraction/chat.
OPENAI_API_KEY=your-existing-local-secret
AI_MODEL=your-existing-structured-output-model
# Optional; otherwise FFmpeg is resolved from PATH.
# FFMPEG_PATH=C:/tools/ffmpeg/bin/ffmpeg.exe
```

See [Azure setup and decision](azure-voice-setup.md) for resource creation and key collection.
The defaults are Azure Speech and Azure Translator. Initial audio uses one Speech
SDK session returning both original transcript and translation. It does not call
the text Translator endpoint afterward. Preparing unchanged text with the same
target reuses the saved translation. Corrected text or a different target uses
Azure Translator, requiring its optional separate credentials; there is no silent
OpenAI fallback. Select Keep original only if text translation is not configured.

Secrets stay server-side. Usage draws on the selected Azure resource's free quota
or paid plan, independently of mock WhatsApp. `azure-cognitiveservices-speech` is
the new Python dependency; existing HTTPX handles text translation. FFmpeg remains
required. The Dockerfile includes audio/TLS runtime libraries. A bounded hidden
worker isolates the native SDK, sends normalized PCM from memory, aggregates all
final segments, and is killed/reaped on cancellation or a 180-second deadline.
Long uploaded recordings may take substantial processing time: one session does
not imply a measured latency guarantee. Configure reverse-proxy timeouts accordingly.

Auto mode identifies among en-IN/hi-IN/mr-IN at the start. It does not promise
mid-sentence language-switch detection. Explicit source=target uses transcription
and copies the original into the target field. Translation-only and source-locale
support must be verified on the chosen Azure resource in the pending live check.

OpenAI adapters remain selectable explicitly with `VOICE_PROVIDER=openai`,
`VOICE_MODEL=gpt-transcribe` and/or `VOICE_TRANSLATION_PROVIDER=openai`.
Use `VOICE_PROVIDER=disabled` to disable speech. Unknown values fail explicitly.
The separate home-field extraction and other chat AI still use OpenAI.

## Audio handling

- Supported upload content types cover WAV, MP3, OGG/Opus, WebM, M4A/MP4 and FLAC.
- Maximum upload: 10 MiB; maximum decoded duration: 120 seconds. The JSON request
  limit remains unchanged; only the exact audio-upload route has the larger limit.
- Uploads stream into a bounded buffer after authentication and ownership checks.
  User-provided URLs and filesystem paths are not accepted.
- FFmpeg is resolved from `FFMPEG_PATH`, PATH, or the bundled `imageio-ffmpeg`
  executable on supported desktop wheels. An explicit invalid override fails
  instead of silently switching decoders. FFmpeg decodes with an explicit format and restricted protocols, no shell,
  a 20-second timeout, and capped output duration. Empty/invalid/very quiet audio
  is rejected. Valid media becomes mono 16 kHz PCM WAV for the speech provider.
- Original uploaded bytes exist only in memory and a temporary decoding file,
  removed after decoding. The database retains the input hash, processing metadata,
  transcripts, translations, previews and confirmation evidence, not raw audio.
  Provider-side retention follows the configured provider's terms.
- Spoken English and synthetic Marathi were live-tested. Hindi language hints
  and text targets are implemented; actual Hindi speech, code-switching,
  noisy shop recordings and broader human accuracy remain to be evaluated.

### Live Marathi verification on 6 November 2026 IST

The existing Azure integration passed a synthetic Marathi recording with both
auto source detection translated to English and explicit Marathi source/target.
Recognition retained cricket, movies, nine-foot distance and sunlight; uploads
left home/sale/consent state unchanged. The two sample uploads took about seven
seconds each; this does not establish a sub-five-second final voice result.
The chat recorder still targets English for review; the dedicated API supports
Marathi output. No replacement voice integration was added.

Reproduce with `python -m scripts.check_marathi_voice --live`. It synthesizes test
speech with the configured Azure resource, uploads through the existing route
and saves local evidence under `output/text-final-acceptance-2026-11-06/`.
This makes provider calls. Real shop noise, code-switching and human accent
accuracy remain outside this synthetic sample.

## API and adapter boundary

All routes use existing session authentication, ownership and same-origin checks.

| Route | Purpose |
| --- | --- |
| `POST /api/customers/{id}/voice?event_id=...&version=...` | Raw audio body with audio Content-Type; optional `source_language=auto/en/hi/mr` and `target_language=en/hi/mr` |
| `GET /api/customers/{id}/voice` | Last 20 saved voice drafts, including statuses; supports reload/review |
| `POST /api/voice/{id}/prepare` | Correct transcript, optionally translate it, and prepare a home/note preview |
| `POST /api/voice/{id}/confirm` | Atomically apply a reviewed preview exactly once |
| `POST /api/voice/{id}/discard` | Close an unused draft without changing the customer |

Prepare request:

```json
{
  "revision": 1,
  "customer_version": 2,
  "transcript": "The sofa is nine feet away.",
  "purpose": "home",
  "target_language": "hi"
}
```

Confirmation uses the new draft revision returned by prepare:

```json
{
  "revision": 2,
  "customer_version": 2,
  "confirmed": true,
  "home": {"home": {"distance": "9 feet"}}
}
```

For a prepared visit note, send `home: null`. It saves the corrected original
transcript; its translation remains attached to the voice draft and message
provenance. For discard, send `{"revision": 2}`.

`app/voice/contracts.py` defines `SpeechProvider` and `TranslationProvider`.
`service.upload` accepts bytes plus media type and verified user/customer context;
future Meta/Twilio media adapters can download authorized provider media and call
this same service. The current mock WhatsApp message schema remains text/actions:
use these voice routes with its saved customer to exercise audio locally. Actual
WhatsApp media download, sender binding and channel review buttons belong to P08
and the remaining P02 channel flow work. No arbitrary remote-media fetcher exists.

## Recovery and confirmation

Upload event IDs are scoped to user/customer and bound to the audio hash/options.
Identical completed uploads return the saved draft. Conflicting content returns
409. Pending operations have leases and attempt tokens; failures/cancellation leave
retryable drafts. A successful transcript is saved before translation so a failed
translation can retry without a second speech request for sequential adapters.
Azure's combined result is saved atomically: an incomplete combined result is
rejected and retry may repeat the speech session. Network calls do not hold
SQLite transactions. Use the same file/event/options when retrying upload.

Prepare is revision-checked and bound to the current customer version. Changed
visits require a fresh preview before confirmation. Confirm applies the business
action and closes the draft in one transaction; replay of the same confirmation
does not add a second note or repeat home changes. Original speech/translation is
advisory data, never workflow authorization. There is no fabricated success fallback.

## Validation

Azure migration: SDK callback fixtures and HTTP transport fixtures cover combined
processing, segments, credential errors, malformed output, timeouts/cancellation,
translation reuse and target/text changes. These are not real Azure speech results.
Azure credentials, language quality, latency and container runtime verification
remain pending. The earlier live evidence below belongs to OpenAI, not Azure.
Latest full suite: **75 tests passed** (16 voice workflow and 8 Azure boundary tests).

- Before Azure migration: **63 tests passed**, including 12 voice tests.
- Regression tests decode real generated WAV bytes but use labelled provider
  doubles for recognition/translation; a separate test exercises real OpenAI SDK
  multipart serialization against an HTTP transport fixture.
- Live check: a 10.28-second Windows-generated English recording was transcribed
  correctly, translated into Hindi and Marathi, and yielded distance, lighting,
  usage and budget fields. Explicit confirmation saved those fields without
  confirming the assessment or recording a sale. This is a sampled success, not a
  general speech/language accuracy certification.
- TypeScript/Vite production build passed. See `docs/validation.md` for UI evidence.

To run the selected providers with an approved synthetic WAV (consumes quota/credits):

```powershell
.venv/Scripts/python.exe -m scripts.check_voice --audio path/to/synthetic.wav --live
```

The script uses an isolated temporary database, never the active customer database.
It changes translation target during review, so configure the optional Translator
key as well as the Speech key and existing OpenAI extraction credentials for that
full check. No live WhatsApp delivery is claimed by this check.
