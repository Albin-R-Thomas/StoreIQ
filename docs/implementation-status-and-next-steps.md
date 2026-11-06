# Store IQ: implementation status and next steps

Updated: 5 November 2026. Internal project handoff; use synthetic customers and approved test recipients only.

## Current position

Store IQ has a website with text and reviewed voice uploads, plus an authenticated mock WhatsApp API/CLI that shares its customer journey. The mock uses interchangeable adapter contracts and a persistent inbox/outbox. Audio transcription and English/Hindi/Marathi translation are implemented; Azure is now the default combined speech provider, with live Azure validation pending credentials. Prior live samples used OpenAI. Real WhatsApp transport and label-photo recognition remain absent.

This checklist reflects the working tree, including changes not yet committed. **Done means implemented within the stated scope; it does not mean production-ready or verified on real WhatsApp.** Unchecked items are pending implementation, integration, validation or external setup, as specified.

### Azure provider decision (5 November 2026)

- [x] Replaced composer file upload with microphone recording: Record, Stop,
  Cancel, automatic language detection and English text for review/Send. Stops
  microphone tracks on completion, failure, cancellation and customer navigation.

- [x] User reports Azure transcription/translation working after key setup.
- [x] Simplified chat UI: upload voice button beside Send, automatic input-language
  detection and English output in the existing editable message box. Removed the
  standalone voice controls. User presses Send to submit reviewed English text.

- [x] Azure Speech combined transcription/translation adapter and unchanged-preview
  translation reuse; replaces the proposed Deepgram + Azure sequence.
- [x] Optional Azure Translator adapter for corrected text or changed targets;
  no automatic provider fallback. See [required keys and setup](azure-voice-setup.md).
- [ ] Configure Speech F0 credentials; optionally configure Translator F0 credentials.
- [ ] Run live Azure recordings and measure latency/English-Hindi-Marathi accuracy.
  Prior live speech evidence below is OpenAI evidence, not Azure validation.

Prompt: Configure the Azure voice POC following docs/azure-voice-setup.md without
printing secrets. Run scripts.check_voice with --live --speech-only on an approved
synthetic recording, then the full review/extraction check if optional Translator
credentials are available. Measure latency and human-review Hindi/Marathi outputs;
record actual evidence and leave unavailable checks pending.

## Requirements and evidence

| Source | Role |
| --- | --- |
| [Contest brief](../6_Reliance_Digital_Store_IQ_Contest_28Oct2026.pdf) | Required WhatsApp TV journey, voice/photo inputs, floor constraints, judging and submission |
| [Store visit findings](<../Store_Visit_Findings_Reference_27Oct2026 (1).pdf>) | Home assessment, explanation, full-cost disclosure and installation follow-through problems |
| [Summary v14](../store-iq-summary-v14.pdf) | Example generated synthetic quote; not a separate requirements specification |
| [Journey specification](tv-store-associate-flows.md) | Proposed detailed conversation and website behavior; not proof every flow is implemented |
| [Architecture](architecture.md) | Active application and persistence boundaries |
| [Mock WhatsApp contract](mock-whatsapp.md) | Implemented adapter, endpoints, reliability behavior and limits |
| [Validation evidence](validation.md) | Latest full run: 75 passing tests, including 13 messaging, 16 voice workflow and 8 Azure boundary tests |
| [Historical review and fixes](../improvments.md) | Opening assessment supersedes older defect descriptions below it |
| [FDK integration plan](fdk-uat-update-plan.md) | Planned data/provider work; predates the new mock messaging foundation |

## Done: web application and business journey

- [x] **D01 — Associate/admin identity:** password verification, saved roles, expiring sessions, ownership checks and same-origin writes. Accounts are synthetic; production identity/OTP is not implemented.
- [x] **D02 — Customer records:** separate associate lists, permanent serials, duplicate-name handling, IST activity filters, history and web resume.
- [x] **D03 — Guided text journey:** saved steps, contextual buttons, inline forms, exact text commands, interruptions and pause/resume.
- [x] **D04 — Home assessment:** text extraction, one missing question at a time, explicit Unknown answers and human confirmation.
- [x] **D05 — Recommendations and comparisons:** stock/budget/preference filtering, home-related ranking and reasons, comparison and grounded AI verdict using local synthetic facts.
- [x] **D06 — Physical-demo evidence:** preferred TV and reason, one-TV demo path, repeat/unavailable handling and downstream gates.
- [x] **D07 — Complete cost:** individual site checks, required/optional extras, unknown-charge holds, deterministic quote arithmetic and synthetic finance calculation.
- [x] **D08 — Customer-specific closing gates:** assessment/demo prerequisites, dated offer eligibility, payment choice and blocking expert holds. Broader offer visibility still needs P04 below.
- [x] **D09 — Synthetic sale:** explicit sale confirmation, atomic local stock decrement and frozen purchase quote. No external order, payment capture or finance approval.
- [x] **D10 — Local follow-through:** owned delivery, installation and working-check tasks, due notifications, dependency-aware reopening and evidence before closure. No resQ/carrier integration.
- [x] **D11 — Summary and PDF:** customer-safe summary, site/shortlist/owner details, versioned PDF, recipient-bound preview, consent, expiring/revocable snapshot links and dependency-based staleness. Sharing is simulated.
- [x] **D12 — Expert workflow:** saved requests, deduplication/reopening, attributed replies, assignment, follow-up, internal notifications and escalation cycles.
- [x] **D13 — Training and review:** persisted practice sessions, attempts, feedback and seven-step scoring with partial/applicable evidence. Approved shift video and broader training validation remain pending.
- [x] **D14 — Written language foundation:** English/Hindi/Marathi coaching and deterministic guided prompts. Whole-site coverage and speech quality are not certified.
- [x] **D15 — Store administration:** editable synthetic catalogue, stock, prices, offers, charges, finance and approved knowledge records.
- [x] **D16 — AI and retrieval:** OpenAI structured extraction/answers, BM25/vector fusion, source checking, atomic reindexing and visible retrieval fallback. Commercial values stay outside generated product chunks.
- [x] **D17 — Local deployment foundation:** SQLite transactions/audit records, health routes, Docker packaging and persistent-volume configuration. External hosting and production operations remain pending.

Implementation locations: [web API](../app/web/api.py), [domain rules](../app/web/domain.py), [flow](../app/web/flow.py), [intelligence](../app/web/intelligence.py), [storage](../app/web/store.py), and [frontend](../frontend/src).

## Done: mock WhatsApp foundation

- [x] **D18 — Adapter contracts:** normalized incoming text/action events, outgoing messages, reply buttons, send receipts and delivery updates; `MessagingAdapter.decode` and `send` isolate provider details.
- [x] **D19 — Mock adapter:** durable simulated acceptance receipts, stable retry keys and no messaging network requests.
- [x] **D20 — Shared journey bridge:** mock text/actions use existing saved customers and business rules; visits can resume on the website.
- [x] **D21 — Inbox/outbox:** durable event identity, conflicting-ID rejection, action/outbox transactions, explicit transport retry and ordered multipart replies.
- [x] **D22 — Recovery safeguards:** stale-version rejection, processing leases, pending AI-message recovery, cancellation handling and receipt-bound monotonic delivery updates.
- [x] **D23 — Protected simulator endpoints:** session authentication, ownership enforcement and development/demo guards under `/api/messaging/mock`.
- [x] **D24 — CLI walkthrough:** `python -m scripts.try_mock_whatsapp` runs deterministic home assessment without a phone or AI call.
- [x] **D25 — Messaging regression coverage and contracts:** 51 tests passed at the mock-messaging milestone; changed Python files passed Ruff with E501 excluded; OpenAPI regenerated. A second test adapter exercises unchanged business calls. See D26 for the newer voice milestone.

- [x] **D26 — Reviewed voice input (P06 core):** audio upload/validation, speech provider adapter, optional English/Hindi/Marathi text translation, original transcript preservation, correction, home/note preview and explicit confirmation. Chat UI and reloadable drafts are implemented. The latest suite has 63 passing tests and a synthetic English recording passed live transcription, Hindi/Marathi translation and home extraction. See [voice input](voice-input.md); live channel media and broader speech evaluation remain pending.

Key files: [contracts](../app/messaging/contracts.py), [adapters](../app/messaging/adapters.py), [service](../app/messaging/service.py), [router](../app/messaging/router.py), [tests](../tests/test_messaging.py).

Current stable business calls:

```python
await service.receive(event, authenticated_associate, adapter)
await service.dispatch(outbox_id, authenticated_associate, adapter)
service.delivery(outbox_id, update, authenticated_associate, adapter.name)
```

Provider-specific authentication, payload decoding, recipient mapping and transport must remain at the integration boundary. Only the mock provider is implemented. Selecting Meta/Twilio in configuration does not create their implementations.

## Recommended next sequence

For development without a real phone number: **P01 → P02 → P03**, then complete **P04–P07** and the mock portions of **P09–P11**. P01 is optional; P02 can be implemented and tested through the existing API/CLI first.

Arrange the approved data and provider access needed for P05/P08 while developing locally. Add **one** live provider in P08 when the test environment is available, finish live delivery/media checks, and complete P11/P12. Implementing both Meta and Twilio is not necessary for a first live demo. P13 is a separate production backlog.

## How to use the module prompts

Copy one prompt below to start that module. Each asks for implementation, relevant tests, contract/documentation updates and an accurate status update. Do not mark the entire module done when only its mock or code portion is complete; split completed subtasks from external verification still pending.

Repository note: `AGENTS.md` references `postman/skills/api-engineer/SKILL.md`, which was missing during the mock work. The user explicitly authorized proceeding without it in this conversation. Preserve that authorization in this session; if the skill is restored, read it for subsequent API work. Do not confuse the unserved legacy Meta/PostgreSQL scaffold with the active messaging module.

## Pending modules and copy-ready prompts

### P01 — Mock WhatsApp chat console

- [ ] **Pending — optional development aid.** Recommended next if we want to test conversations interactively without a phone.

**Depends on:** existing mock API. **Done when:** an authenticated associate selects a synthetic customer, sends text/actions, sees persisted replies and simulated delivery state, and resumes after reload. Old buttons cannot mutate a newer visit. Input/navigation buttons retain their distinct behavior. Include a way to inspect/retry failed messages; preserve demo-only access.

```text
Implement P01 from docs/implementation-status-and-next-steps.md: a mock WhatsApp chat console inside the existing Store IQ website. Read docs/mock-whatsapp.md and reuse /api/messaging/mock endpoints and existing authentication. Support customer selection, text, contextual actions, required input forms, website navigation, persisted history, simulated delivery state and explicit retry. Clearly label it as a simulator. Keep provider logic out of React and prevent stale buttons from submitting against a newer customer version. Verify the interface in the browser when available, test meaningful failure cases, build the frontend, and update this checklist with the exact validation limits.
```

### P02 — Channel conversation context and customer selection

- [ ] **Pending — required for a usable channel journey.** The current simulator requires an explicit existing customer ID/version on every event.

**Depends on:** messaging foundation; P01 optional. **Done when:** a logical associate can start a shift, create/select/resume a customer and complete structured inputs without manually passing customer IDs. Context is durable and scoped to the associate/channel. Old replies resolve to their original visit and revision. Web resume sees the same records.

```text
Implement P02 from docs/implementation-status-and-next-steps.md. Add provider-neutral, persistent conversation context for shift start, new customer, customer list/date filters, customer selection and resume. Resolve normalized text and button replies to the correct saved visit, including multi-step input collection for demo, site, sale and consent actions. Keep logical associate identity separate from phone numbers; use authenticated synthetic bindings for the mock. Reuse the existing journey and validation rules, preserve the service call interface, and reject stale or cross-customer replies. Test duplicate input, reconnect, customer switching and web/channel resume. Update OpenAPI, documentation and this checklist.
```

### P03 — Background processing and automatic delivery recovery

- [ ] **Pending — required for reliable live messaging.** The current request waits for processing; transport retry is manual.

**Depends on:** messaging inbox/outbox. **Done when:** ingress durably queues work and returns promptly; a worker safely resumes after restart, bounds retries and exposes failures. Per-conversation ordering and multipart ordering hold. Provider acceptance remains distinct from delivery. HTTP acknowledgement and a user-visible WhatsApp acknowledgement are measured separately.

```text
Implement P03 from docs/implementation-status-and-next-steps.md. Extend the existing messaging inbox/outbox with durable background processing, bounded retry/backoff, attempt ownership, restart recovery and inspectable terminal failures. Preserve per-conversation ordering and stable idempotency keys without rerunning business actions. Keep network/model calls outside SQLite transactions and retain the documented single-service deployment boundary. Add prompt acknowledgement of queued work and a provider-neutral user-visible checking reply for slow operations. Test duplicate workers/events, timeout, cancellation, restart, ambiguous transport success and partial multipart failure. Do not claim exactly-once delivery or sub-five-second real WhatsApp performance from mock tests. Update contracts, docs and this checklist.
```

### P04 — Promotion visibility and commercial gate audit

- [ ] **Pending — correctness requirement.** Bootstrap currently exposes all local offers while customer-specific quote/chat paths apply gates.

**Depends on:** existing web/domain code; independent of provider selection. **Done when:** the required associate shift brief remains useful, but customer-facing promotional closing content consistently respects assessment/demo gates across API, website and messaging. Direct price questions still receive honest answers.

```text
Implement P04 from docs/implementation-status-and-next-steps.md. Audit bootstrap, shift briefing, catalogue, comparison, chat, summary and messaging for premature customer-facing promotional content. Define and enforce the distinction between associate-only offer-change awareness before the shift and customer-specific offers unlocked after confirmed assessment and a physical demo. Preserve truthful direct price answers and existing payment/sale gates. Add regression tests for before/after-demo visibility, expired offers and finance exclusions. Update the affected contracts, documentation and checklist.
```

### P05 — Approved data imports and optional FDK integration

- [ ] **Pending — approved factual inputs are required; FDK specifically is an integration choice.** The active catalogue and commercial terms are synthetic local records.

**Depends on:** approved test data; successful authorized JSON samples for any FDK adapter. **Done when:** imported/manual/fixture provenance is explicit, missing specifications remain unknown, refresh is atomic, stale data is visible and changed facts invalidate pre-sale previews. Listing availability is not represented as confirmed physical stock. Charges and finance need their own approved source.

```text
Implement P05 from docs/implementation-status-and-next-steps.md. Read docs/fdk-uat-update-plan.md and the supplied FDK reference. Build source-aware catalogue/commercial ingestion with stable external IDs, nullable facts, currency/variant handling, provenance, timestamps, atomic refresh and explicit stale-data behavior. Support an approved fixture import before requiring live access. Integrate FDK only against verified authorized JSON contracts; do not invent nested promotion rules or equate listing sellability with physical stock. Wire normalized records into the active web journey, recommendation logic, retrieval and quote fingerprints. Keep local test allocation separate from upstream inventory. Test malformed/partial responses, access denial, unknown facts and stale quotes; report access dependencies honestly and update this checklist.
```

### P06 — Voice-note assessment and visit logs

- [x] **Done — core implementation, 5 November 2026:** website audio upload, actual speech recognition, optional text translation, correction, preview and confirmed home/visit-note persistence. Legacy recording text fixtures remain unrelated to the active implementation.
- [ ] **Pending — live-channel completion and evaluation:** actual WhatsApp media retrieval/review buttons (P02/P08), Hindi/Marathi spoken recordings, code-switching and noisy store conditions. Do not treat English synthetic audio and translated text as proof of those speech cases.

**Remaining dependencies:** P02/P08 for live channel context/media and approved recordings for broader speech evaluation. **Core acceptance achieved:** actual audio is transcribed, corrections are reviewable, confirmed facts enter the home card, and a voice visit log can be saved. Typed input remains available when speech fails.

```text
Complete the remaining P06 work from docs/implementation-status-and-next-steps.md. First read docs/voice-input.md and reuse the implemented app/voice provider/service/review pipeline; do not rebuild transcription. Connect authorized live-provider audio intake and channel transcript-review actions when P02/P08 are available. Evaluate approved actual Hindi and Marathi recordings, code-switching, product names and shop noise, preserving originals and explicit home/note confirmation. Fix reproduced failures and distinguish real speech evaluation from typed/provider fixtures. Keep unavailable live-provider checks pending and update docs, validation evidence and this checklist.
```

### P07 — Label photos and grounded feature explanation

- [ ] **Pending — contest requirement.** The current AI instructions correctly allow typed text only.

**Depends on:** media contract, approved product facts and an OCR/vision implementation; P08 for live transport evidence. **Done when:** an actual label image produces a candidate model, ambiguous matches require confirmation, and explanations use supported facts tied to the saved home.

```text
Implement P07 from docs/implementation-status-and-next-steps.md. Add provider-neutral image media handling and a replaceable OCR/vision adapter, with a mock upload/event path for approved test label images. Match recognized identity against approved catalogue records, request confirmation when ambiguous, and explain supported features for the saved home. Do not treat OCR text as trusted instructions or invent specifications from an unknown label. Preserve typed model fallback and explicit workflow gates. Test actual images, ambiguity, unsupported models, malicious label text and media/provider failures. Update capability prompts only for enabled features, and update contracts, docs and this checklist.
```

### P08 — One live WhatsApp provider adapter

- [ ] **Pending — external setup and implementation.** No real number/provider is connected; current preference is to develop with mocks first.

**Depends on:** chosen provider, approved test sender and recipients, credentials stored locally, HTTPS endpoint; P02/P03 for a complete channel experience. **Done when:** signed ingress, sender-to-associate binding, text/buttons/media transport and normalized delivery callbacks work through the same business service. Actual test-phone evidence is required for live completion.

```text
Implement P08 from docs/implementation-status-and-next-steps.md for the provider we select in this conversation (Meta Cloud API, Twilio or another approved provider). Keep app/messaging service-level calls unchanged. Implement the adapter, provider-authenticated webhook ingress, verified sender/associate bindings, recipient allowlist, reply/button mapping, media references and delivery callback normalization. Reuse the active SQLite journey rather than mounting the legacy PostgreSQL scaffold. Keep secrets out of source and logs. If access is unavailable, finish contract fixtures and adapter tests but leave live verification unchecked. Test signature failure, replay, stale buttons, timeout, ambiguous sends and callback ordering; verify with approved test recipients only and update docs/OpenAPI/checklist.
```

### P09 — Consented summaries and delayed expert/task notifications

- [ ] **Pending — channel delivery integration.** PDF/consent snapshots, expert replies and local reminders already exist.

**Depends on:** P02/P03; P08 for actual external delivery. **Done when:** approved notifications queue through the common adapter and reach the original visit/recipient without changing the active customer. Customer summaries require current preview/consent checks, including revocation before dispatch. Internal tasks do not imply permission to contact customers.

```text
Implement P09 from docs/implementation-status-and-next-steps.md. Connect existing summary sharing, expert replies and due-task notifications to the provider-neutral outbox. Reuse recipient-bound PDF previews, consent, expiry/revocation and quote fingerprints; recheck permission before sending queued customer content. Keep associate notifications distinct from consented customer contact, preserve original visit identity and enforce test-recipient allowlists. Handle provider messaging-window/template restrictions at the adapter boundary. Prove the flow with the mock first and leave real delivery unchecked until verified. Test revoked consent, stale previews, duplicate reminders, switched active customer and delivery retries. Update docs, contracts and checklist.
```

### P10 — Shift training and language completion

- [ ] **Pending — required training content and language quality work.** Practice persistence and written Hindi/Marathi foundations are already implemented.

**Depends on:** approved short video and reviewer input; voice evaluation depends on P06. **Done when:** shift brief includes the approved video/question, progress remains separate from visits, and the complete demonstrated journey has reviewed English/Hindi/Marathi prompts, corrections and failure messages.

```text
Implement P10 from docs/implementation-status-and-next-steps.md. Complete the shift brief with an approved short training video and one question, preserving existing resumable practice and reporting. Audit English, Hindi and Marathi across the demonstrated web/channel journey, including buttons, validation errors, cost/finance explanations and summaries. Preserve model names, amounts and the three-line/three-button limit. When voice is enabled, evaluate code-switching and product-name transcription using approved test recordings. Do not mark linguistic quality verified from automated string checks alone. Record any missing content/reviewer dependencies and update docs and checklist.
```

### P11 — End-to-end usability and reliability validation

- [ ] **Pending — final acceptance evidence.** Local backend regression coverage exists; current browser/mobile and real-channel validation do not.

**Depends on:** modules selected for the release; live checks depend on P08. **Done when:** a reproducible TV visit covers assessment, correction, explanation, options, demo, full cost, sale, consent, installation and working check. Validate failures and a new associate's ability to follow it, not only the happy path.

```text
Complete P11 from docs/implementation-status-and-next-steps.md. Run the current regression suite and frontend build, then verify the full TV journey through the browser and mock channel. Cover reload/resume, old buttons, customer switching, unknown facts, stock/price changes, provider failures, consent refusal, installation delays and final working checks. If live WhatsApp is configured, repeat on an approved test phone and measure user-visible first response, line/button usability and delivery states. Record seven-step evidence and one coaching improvement. Separate mock, live, browser and human-review evidence; fix reproduced defects and update docs/validation.md and this checklist without claiming unavailable checks passed.
```

### P12 — Contest deployment and submission package

- [ ] **Pending — deployment/access and submission artifacts.** Docker packaging exists; a verified hosted live entry is not established.

**Depends on:** approved hosting, test channel, selected release modules and P11. **Done when:** HTTPS deployment and restart persistence are verified, a ten-minute demo is rehearsed, and the test number, code link, at-most-five-minute video and one-page design note are ready for internal submission. The brief says 6 November, 18:00; confirm submission timezone with the organizer.

```text
Prepare P12 from docs/implementation-status-and-next-steps.md. Package the selected Store IQ release for the approved demo environment, preserving HTTPS/session settings, persistent storage, local secrets and test-only recipients. Validate startup, readiness, restart persistence and rollback instructions. Prepare a one-page design note, a ten-minute live-demo script, a submission video plan no longer than five minutes and the required code/test-number references. Clearly identify any contest criteria still unmet. Do not publish externally or send a submission unless explicitly authorized; prepare reviewable artifacts first. Update deployment evidence and this checklist.
```

### P13 — Production operations and real retail integrations

- [ ] **Deferred — separate scope beyond the synthetic contest implementation.** These are not prerequisites for building the mock experience.

**Depends on:** explicit production requirements, organizational identity/data policies and authoritative integration contracts. **Remaining areas:** production identity/OTP, multi-store tenancy, backup/restore, operational monitoring, load/adversarial evaluation, multi-replica persistence if needed, and real inventory/order/payment/resQ integrations. Purchase corrections currently create manager-review tasks; they do not implement refunds or order amendments.

```text
Scope and implement the explicitly selected part of P13 from docs/implementation-status-and-next-steps.md. First establish production requirements and authoritative contracts for that part; do not replace the entire architecture or add speculative services. Preserve tenant/associate boundaries, auditability, consent and the advisory-only AI boundary. Keep real inventory reservations, orders, payments, amendments and installation jobs distinct from local synthetic records. Add operational failure/restore tests appropriate to the chosen scope and document rollout dependencies. Leave unrelated production areas unchecked and update this checklist with concrete completion evidence.
```

## Completion discipline

- Update this file after each module with date, implemented scope, affected files and verification evidence.
- Keep incomplete external setup and validation visible even when implementation code exists.
- Preserve already working web rules and provider-neutral service calls as channels are added.
- Do not report backend regression counts as live WhatsApp or production validation. Use the separately recorded audio/browser evidence for those capabilities.
- Historical validation includes sampled live AI and Docker checks; the mock change did not rerun those checks.
- Five pre-existing Ruff findings in unrelated simulation/FDK scripts remain recorded in the validation notes; fix them separately when appropriate.
