# Validation evidence

## Microphone composer — 5 November 2026

- Replaced file selection with browser MediaRecorder capture. Record/Stop produces
  a clip for the existing auto-language/English voice endpoint. Cancel discards
  locally; retry retains the clip/event ID. Recording and processing block Send,
  and translated text remains editable before explicit Send.
- TypeScript/Vite build passed; changed Python header code passed Ruff (E501
  excluded); `git diff --check` passed. Permissions Policy now allows microphone
  for self only, with camera and geolocation still disabled.
- Headless Edge checks used a Chromium synthetic microphone with real MediaRecorder,
  actual recorded WebM decoding, and labelled speech/translation provider fixtures.
  Record, Stop, discard without upload, retry with the same event ID, permission
  denial, automatic source/English target, preservation of typed text, and no
  automatic message send passed. Tracks were observed ended after Stop, Cancel and
  customer navigation. Desktop/mobile screenshots inspected.
- No physical microphone or new live Azure recognition check was performed by the
  agent. User should allow browser microphone access on localhost and verify their
  actual recording. HTTPS is required away from localhost. A scheduled stop at
  119 seconds and the server's 120-second / 10 MiB limits bound recording size.

## Composer voice upload — 5 November 2026

- User reports Azure transcription and translation working in the running app.
  This is user-reported validation; no new agent-measured Azure latency or language
  accuracy result is claimed.
- Removed the separate voice panel and language/purpose/save controls from chat.
  Upload is now a 44px button beside Send. Every UI upload requests automatic
  source detection and English translation, then inserts English into the normal
  message box for review. Sending remains an explicit user action.
- TypeScript/Vite build passed. Headless Edge checks with labelled provider
  fixtures passed at desktop and 390px mobile widths: button placement, file
  chooser, auto/en parameters, no automatic message send, preservation of typed
  text, upload failure and same-event retry, no horizontal overflow or page errors.
  Screenshots visually checked. In-app browser initialization failed, so the
  existing standalone headless test setup was used.
- Docker image rebuilt and container restarted; healthy, host page HTTP 200 at
  http://127.0.0.1:8000. No backend API contract or provider implementation changed.
  Original audio transcripts remain stored as voice drafts; the reviewed English
  message uses the existing text-chat endpoint. Composer drafts are not restored
  after reload. The dedicated voice review API remains available to API callers.

## Azure voice migration — 5 November 2026

- Full backend suite: **75 tests passed**, including 16 voice workflow tests and
  8 Azure boundary tests. Changed Python files passed Ruff (E501 excluded), and
  `git diff --check` passed. No frontend change was needed for this migration.
- Installed Microsoft Speech SDK 1.53.0 locally. A real native SDK construction
  check accepts PCM stream, target language and en-IN/hi-IN/mr-IN auto-language
  configuration without opening a recognition session.
- SDK callback fixtures exercise continuous multi-segment aggregation, original
  transcription plus translation, same-language output, no-speech, authentication
  cancellation and worker timeout/cancellation cleanup. HTTP transport fixtures
  exercise Translator v3 request serialization, regional authentication headers,
  quota/provider errors and malformed/wrong-target responses. These do not prove
  real Azure recognition, connectivity, free-tier eligibility or translation quality.
- HTTP/SQLite workflow tests establish one combined audio call, zero text calls
  on initial combined upload and unchanged preview, corrected-text/target refresh,
  partial-result rejection, replay protection and no stale translation reuse when
  retrying an older upload. Existing review/confirmation safety checks still pass.
- Postman CLI 1.85.0 status checked: initialized, signed out. Owner/mock search was
  skipped. Orbit search returned a fast-transcription endpoint that explicitly
  excludes translation; it was not adopted. Implementation instead follows the
  official Speech SDK and Translator contracts linked in azure-voice-setup.md.
  The existing Postman HTTP simulation covers OpenAI, not the native Azure Speech
  SDK WebSocket protocol; no Azure Postman simulation or live success is claimed.
- Local `.env` provider selectors now use Azure; missing key/region placeholders
  were added without replacing existing secrets. Live Azure checks are pending
  user credentials. Use `scripts.check_voice --live --speech-only` for an isolated
  Speech-only note check, reporting elapsed upload time. Full home extraction and
  changed-target checks also need optional Translator and existing OpenAI keys.
- Remaining: actual English/Hindi/Marathi recordings, code-switching/store noise,
  measured latency, live provider failures and Docker native-runtime verification.
  Earlier live evidence below belongs to OpenAI, not Azure.

## Reviewed voice input — 5 November 2026

- Full backend regression run: **63 tests passed**, including 12 voice tests.
  Voice tests exercise real local WAV decoding with provider doubles, SDK multipart
  transport with an HTTP fixture, upload replay/conflicts, failed translation retry,
  cancellation, invalid/silent/overlong/oversized audio, authorization, stale
  customer/draft versions, correction, note safety and idempotent confirmation.
- Live configured-provider check passed on a **10.28-second synthetic English
  recording**, generated locally by Windows speech synthesis. Transcription matched
  the sentence; Hindi and Marathi text translations were returned. Extracted home
  fields were `distance=8 feet`, `light=bright`, `use=watch cricket and movies`,
  and `budget=INR 70,000` (the returned value used the rupee symbol). The isolated
  customer remained unchanged until confirmation, then retained unconfirmed
  assessment and no sale. No real customer recording or messaging provider was used.
- Strict TypeScript/Vite production build passed. Changed Python files pass Ruff
  with the existing E501 exclusion; OpenAPI regenerated and diff whitespace checked.
- The in-app browser connection failed before opening a tab. A separate headless
  Edge/Playwright check against an isolated local server with **simulated speech
  and translation** passed desktop upload, transcript correction, edited home
  preview/save, reload/resume, and mobile note-preview/discard, without page errors.
  Screenshot review exposed an oversized form in the fixed composer; the form was
  moved to the scrollable conversation area and the UI check repeated.
- Not verified: actual Hindi/Marathi speech, code-switching, store noise, live
  WhatsApp media, microphone recording or speech output. Text translations from
  an English recording are not evidence of recognition accuracy in those languages.
  No new Docker image build was performed; FFmpeg installation is added to its recipe.
- See [voice setup/API/limits](voice-input.md) and opt-in `scripts.check_voice --live`
  for the reproducible live backend check. Live runs use a temporary database.

## Mock WhatsApp adapter — 4 November 2026

- Installed the declared project dependencies into the local `.venv`.
- `.venv/Scripts/python.exe -m unittest discover -s tests -q`: **51 tests passed**,
  including 13 messaging tests using isolated SQLite databases and HTTP routes.
- Messaging coverage includes web resume, duplicate/conflicting events, stale
  versions, sale/stock idempotency, provider substitution, timeout, malformed
  receipts, cancellation, partial transport success, expired processing leases,
  concurrent website edits, ordered multipart replies, receipt-bound monotonic
  callbacks, access isolation and disabled mock endpoints.
- Changed Python files pass Ruff with the repository's existing E501 exclusion;
  Python compilation and `git diff --check` pass. The broad Ruff check still reports
  five existing findings in `check_ai_simulation.py`, `check_fdk_auth.py` and
  `check_fdk_auth_matrix.py`; those unrelated scripts were not changed.
- Regenerated `postman/specs/store-iq.openapi.json` from the active application.
- No real WhatsApp, Meta, Twilio, voice/photo, live AI or browser validation was
  performed for this change. Mock accepted/delivered/read results are simulations.
  See [mock channel setup and limits](mock-whatsapp.md).

## Automated local checks

- `python -m unittest discover -s tests -q`: **24 tests passed**, including the
  commercial editor, expert follow-up history and persisted reminder cycles.
- Strict TypeScript compilation and Vite production build passed (309 KB JS,
  93 KB gzip). Python source checks passed with E501 excluded for long prose fixtures.
- `docker compose config --quiet` passed.
- Readiness endpoint returned `{"status":"ready"}` with the durable SQLite store.
- Tests exercise real temporary SQLite databases and HTTP routes. Coverage includes
  per-associate isolation, admin role checks, same-origin enforcement, serial and
  duplicate-name handling, invalid dates, stale writes, invalid payloads, gated
  offers/payment/sale, frozen purchase quote, finance arithmetic, separate delivery /
  installation / working checks, consent and share revocation, and blocked injection.

## Postman stand-in evidence

Postman CLI 1.83.0 ran `associate-ai.sim.yaml` on port 4010. The real application
and OpenAI SDK ran through the stand-in using an isolated temporary database.
The simulation log recorded `/v1/embeddings` and `/v1/responses` requests.

- Index rebuild: HTTP 200.
- Coaching: HTTP 200, `bm25_vector_rrf`, supporting source `samsung-q55`.
- Injected provider outage: upstream HTTP 503, application HTTP 502.
- Retried outage: exactly one saved user message; no fabricated assistant reply.

This establishes SDK transport, schema parsing, index/retrieval wiring and the
observed error path against these fixtures. It does not establish real model
quality or semantic retrieval quality. Owner-mock discovery was skipped because
there is no connected signed-in Postman workspace. Fixtures follow the official
Responses and embeddings shapes.

## Live provider evidence

The initial credential returned AuthenticationError; the application retained
its previous index. After the user replaced the key, `AI_MODEL` was missing from
`.env`; the previous value, `gpt-6-luna`, was restored without changing the key.

`python -m scripts.check_ai_simulation --live` then passed against real OpenAI:

- Embedding rebuild: HTTP 200 using `text-embedding-3-small`.
- Structured text coaching: HTTP 200, `bm25_vector_rrf`, sources `samsung-q55`
  and `display-guide:0`; returned the supported native refresh rate of 120 Hz.
- Two-product comparison: HTTP 200, grounded verdict for Samsung Vision Q55 vs
  TCL Spectrum Q55 with the recorded home needs, a price tradeoff and a physical
  demo suggestion. Sample latency: 11.2 seconds for the comparison endpoint.
- Context follow-up: HTTP 200, correctly returned Samsung Vision Q55 brightness
  of 600 nits with a matching product source.
- Unsupported included-HDMI-cable length: HTTP 200 and the exact missing-fact
  fallback, without inventing a length.
- Injection request: blocked before a model call; no workflow action executed.

These live journey checks use a temporary database and synthetic customers. They
establish model access and the sampled outputs, not comprehensive answer quality,
language quality, retrieval quality or resistance to all adversarial requests.

The running application was restarted to load the new credential. Its persistent
knowledge index rebuilt with HTTP 200, published version 1, `dirty=false`;
`/health/ready` returned HTTP 200. Secret values were not logged or committed.

## PDF and browser checks

A synthetic customer PDF was generated through the same renderer used by the
download route. Poppler rendering exposed an orphaned disclaimer page; spacing was
adjusted; the final one-page rendering was visually inspected with no clipping,
overlap or orphaned disclaimer. The PDF route's content type
and `%PDF` header are covered by the API tests. Original Indic script should use
the browser print view until multilingual PDF font shaping is integrated.

Computer-use browser review could not proceed: the Windows runtime could not
determine the active browser URL with enough confidence and stopped automation.
No desktop/mobile visual or interaction coverage is claimed. CSS responsive rules
and reduced-motion behavior are implemented but need browser review.

## Guided conversation update

The associate chat now renders server-derived prompts and up to three contextual
reply buttons in the thread. Completed message actions remain visible but inactive;
only the current prompt can submit a fresh action. The home card shows context;
workflow inputs (demo preference, site check, extras, follow-up, sale, expert request
and task evidence) open inline in the conversation. The entry conversation includes
Start shift → TV → View stock / Start practice / Skip practice today, plus customer
date filters and three-record pagination. Resuming offers Continue flow, View history
and Open summary. Detailed catalogue, training and summary pages retain return links.

- `python -m unittest discover -s tests -q`: **29 tests passed** after this update.
  New checks cover one-question home answers without a model call, Unknown, Correct,
  demo buttons, cost/offer gates, explicit sale and consent, expert resolution,
  pause/resume and read-only flow presentation.
- Strict TypeScript compilation and the production frontend build passed.
- The existing Postman simulation passed structured coaching, hybrid retrieval and
  upstream outage/retry checks with the new response shape.
- `python -m scripts.check_guided_chat --live` passed using the real configured
  model: all seven supplied home facts were saved; Correct/Edit/Ask customer were
  offered; expert answer returned the supported Samsung 120 Hz specification with
  sources and Resolved/Ask admin/Ask follow-up; resolving returned to the same saved
  step. Starting the demo showed Demo done/Need another demo/Demo unavailable while
  both demo and sale remained unconfirmed.
- Browser inventory still reported the browser access host unavailable. No new
  browser interaction or screenshot coverage is claimed.

## Deployment verification and remaining limits

Docker image build succeeded with `docker build -t store-iq:local .`.
A disposable container returned HTTP 200 for readiness, demo login, bootstrap
(eight TVs) and the compiled frontend. No real API credential was passed into it.
External HTTPS deployment, sustained load,
multi-store access, production identity/OTP and broad adversarial testing were not
verified. This is a functional local contest implementation with production-oriented
boundaries, not a certification of production readiness or jailbreak immunity.
