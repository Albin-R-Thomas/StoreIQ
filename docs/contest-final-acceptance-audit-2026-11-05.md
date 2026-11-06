# Store IQ contest final acceptance audit

**Verdict: FAIL for final acceptance.** WhatsApp integration and mock removal are not the only remaining limitations. The backend can complete the synthetic selling and handover journey with structured actions, but the documented text conversation still has gaps, slow replies, language failures and missing photo support. No application fixes were made during this audit.

Internal confidential use only. Executed 5 November 2026 UTC, crossing into 6 November IST. The execution timestamps in the evidence are authoritative; the artifact folder uses the audit start date.

## Acceptance scope

Requirements: [associate flows](tv-store-associate-flows.md), the contest PDF dated 28 October and the store visit reference dated 27 October, both in the repository root. The contest requires a ten-minute WhatsApp demonstration, assessment before promotional closing, voice/photo input, a first reply under five seconds, at most three lines/buttons, grounded facts, complete charges and owned follow-through. Judging combines demo and store live-test results equally; this technical audit cannot establish a winning judge score.

This audit acts as an associate through backend text and real HTTP calls, plus structured actions when the text journey stops. It deliberately distinguishes that recovery from a text-only pass. The requested allowed deferrals are:

1. Live WhatsApp provider integration and transport acceptance.
2. Replacement of synthetic catalogue, stock, offers, finance and other mock data with approved sources.

The contest itself requires test data and a test WhatsApp number. Production data replacement is a product objective, not permission to use real customer data during the contest.

## Execution and evidence

- Real Uvicorn server: `http://127.0.0.1:8011`, application `app.main:app`.
- An SQLite backup was made to `output/contest-acceptance-2026-11-05/audit.db`; the server used that separate database. Existing working data was not changed by the HTTP probes.
- Configured live AI and the existing published hybrid index were used for natural text and comparison. No AI stub was used for those requests.
- **81 primary HTTP observations**, including **34 text-message requests**; **21 supplemental HTTP observations**; **20 readiness requests at concurrency five**. These counts are observations, not semantic assertion pass counts.
- **29 additional backend review observations** used real route handlers with isolated SQLite through FastAPI TestClient. These are in-process evidence rather than TCP latency measurements.
- Full regression discovery: **71 tests, 56 passed, 13 failed, 2 errors**, in **61.395 seconds**, exit failure. Voice failures are dominated by unavailable FFmpeg; one test module cannot import Azure Speech. This is not a green release suite.
- Existing Postman provider simulation: passed. Embedding and Responses request events were observed; provider 503 mapped to 502, retained the user message and did not duplicate it on retry. This is simulated outage evidence, not a live provider outage.

Evidence files under `output/contest-acceptance-2026-11-05/`:

| File | Contents |
|---|---|
| `http-evidence.json` | Inputs, responses, versions, messages, source passages and wall-clock durations for the primary run |
| `http-run.log` | Human-readable primary run sequence |
| `supplement.json` | Expert lifecycle, replay, security and invalid-input responses |
| `concurrent-readiness.json` | Twenty readiness timings |
| `first-byte.json` | Independent streaming-client header/body arrival measurement and early-price response |
| `regression.log` | Full regression output and failure traces |
| `outage-check.log`, `simulation.ndjson` | Local provider failure check and matching transport events |
| `acceptance-summary.pdf` | Actual downloaded synthetic purchase summary; content extracted successfully, visual layout not accepted in this backend audit |

The additional 29 observations are saved in `output/improvements-review-evidence.json`. Output files are gitignored; preserve them with the report when transferring evidence. The audit database contains copied local records and should remain local.

Reproduction drivers: `scripts/audit_contest_acceptance.py`, `scripts/audit_acceptance_supplement.py`, `scripts/review_backend_flows.py`, and `scripts/check_ai_simulation.py`. The primary driver requires the separate server and makes paid configured-provider calls. Use a fresh database snapshot for each run because it intentionally records synthetic sales and changes stock. Supplemental assignment currently uses the seeded admin name.

Two original harness expectations need interpretation: revoked links returned **404**, which correctly denies access and is not a defect; the harness initially expected 410 and has been corrected. Sending `TV` to `/api/shift` returned **422** because that endpoint accepts `start` and `skip_practice`; this proves the department-selection conversation is absent there, not a broken documented HTTP schema.

## Scenario acceptance matrix

| Flow or branch | Result | Observed behavior |
|---|---|---|
| Login, ownership, admin restrictions, hostile origin | PASS sampled | Unauthenticated 401, cross-associate 403, associate admin-reply 403, hostile-origin 403 |
| Shift start and skip | PARTIAL | Saves TV shift and skip; no department question/TV selection or conversational brief through shift API |
| Training | PASS sampled | All six seeded questions and all three choices exercised in handler review; finish/resume covered by regressions |
| Seven home facts in one utterance | PASS | Saved seven facts and requested confirmation |
| Combined natural answers and correction | PASS | Sunny/Netflix/cabinet/word-number budget parsed; subsequent twelve-foot correction saved |
| Vague or unmeasured distance | PASS | Did not invent metres/feet from hand lengths; distance remained missing |
| Explicit unknown answers | PARTIAL | Can confirm Unknown fields, but quality of resulting advice needs uncertainty-aware review |
| Early requested price | PASS sampled | Gives structured catalogue price and resumes assessment; does not unlock payment |
| Belief correction | PARTIAL | Grounded explanation and physical check, but slow and no explicit agreement-first opening in sampled English answer |
| Typed feature explanation | PASS content / FAIL latency | Grounded HDMI explanation tied to motion concern; avoids promising a cure |
| Label photo and unclear photo | NOT IMPLEMENTED in active journey | Active coaching requests typed models; no active label-photo recognition path found |
| Recommendations, no match, one match | PASS sampled | Three grounded options; low budgets give no match; one suitable TV supports single-TV demo |
| Comparison | PASS content / FAIL latency | Three-TV verdict with hybrid sources, home fit and tradeoffs; no sale mutation |
| Demo preference by text | PASS sampled | Demo done asks preference; model plus English `because` saves evidence |
| Demo unavailable | PASS | Remains incomplete and blocks offer progression |
| Site check through free text | FAIL | Opens input action; typed site answers do not save site; recovery needed structured action |
| Required and optional cost arithmetic | PASS structured / PARTIAL chat | Optional extras add/remove; quote lines total correctly; chat substitutes a subtotal and link for itemisation |
| Offer and finance | PASS sampled | Early finance 409; full-payment-only discount disappears for finance; fee and full total disclosed |
| Explicit sale | PASS structured / FAIL standalone text | Text asks for form action; structured confirmed-total action creates one test sale |
| Consent, PDF, preview, share, revoke | PASS structured | No-consent share blocked; recipient/PDF preview required; simulated share readable; revocation denies access |
| Changed commercial quote | PASS handler review | Shared quote becomes outdated; post-sale amount frozen |
| Delivery, installation, working check | PASS structured | Early working check 409; ordered completion closes visit; installation problem reopens handover |
| Expert escalation and admin reply | PASS sampled | Deduplicated request, attributed reply, notification, resolution and same-thread reopening |
| Blocking expert uncertainty | PASS handler review | Resolving without decision evidence does not unlock payment |
| Reminders and escalation | PASS regressions / partial wall-clock proof | Existing clock-controlled tests and aged-record handler probes; no five-minute real-time scheduler soak |
| Customer list and serial resume by text | FAIL | Customer list emits website navigation; typing serial 2 attempts home extraction rather than opening customer 2 |
| IST activity dates and manager filter | PASS structured | Invalid/reversed dates rejected; returning customer counted once; associate scopes tested |
| Hindi | PARTIAL | Localized prompt and grounded Hindi answer; belief detection is classified as expert rather than validate |
| Marathi | FAIL sampled | Cricket next-question request saved use but returned English missing-facts fallback |
| Review and seven-step score | PARTIAL | Completed sample earns internal 14/14; reopened installation lowers follow-through; weak evidence semantics remain |
| AI outage and retry | PASS local simulation | 502 without fabricated reply; one retained user message after retry |
| Same-message replay | PASS sampled | Same request ID does not duplicate the answer; different text under same ID silently returns old result |
| Voice runtime | BLOCKED | FFmpeg unavailable and Azure Speech import missing in this environment |

PASS means the sampled behavior held. This is broad scenario coverage, not a claim to have exhausted arbitrary language, provider behavior or concurrency interleavings.

## Latency acceptance

Measured client wall-clock over localhost with the live configured AI. Percentiles use nearest rank. Fast commands and slow AI calls are separated by the explicit examples below; the all-text median alone would be misleading.

| Population | N | p50 seconds | p95 seconds | Maximum seconds | Over 5 seconds |
|---|---:|---:|---:|---:|---:|
| Primary HTTP observations | 81 | 0.033 | 11.120 | 22.685 | 9 |
| Text-message requests | 34 | 0.040 | 16.630 | 22.685 | 8 |
| Readiness with five concurrent clients | 20 | 0.917 | 0.950 | 0.956 | 0 |

| Live operation | Seconds |
|---|---:|
| All seven natural home facts | 6.908 |
| English belief correction | 16.630 |
| Feature explanation | 13.568 |
| Three-TV comparison verdict | 11.120 |
| Site-check answer misrouted to AI | 22.685 |
| Unknown model explanation | 8.969 |
| Missing cable-length fact | 9.751 |
| Hindi belief correction | 12.542 |
| Marathi next-question request | 7.379 |

**Latency verdict: FAIL for backend first reply under five seconds.** `/messages` awaits extraction/retrieval/answer before returning a JSON response; no early backend acknowledgement is emitted. The website has a client-side “Checking the latest details” busy indicator, so this finding does not claim the browser is visually silent. That indicator is not an acknowledged backend/channel reply. The separate `first-byte.json` records header and first-body timing for another live request.

An independent streaming-client probe received both response headers and its first body bytes at **8.228 seconds**, with total completion also **8.228 seconds**. It confirms that this live request produced no early backend reply. This additional probe is outside the 81-request percentile population.

Readiness concurrency does not establish concurrent chat capacity. No realistic associate load test, mobile network test or sustained AI p95 SLO was completed.

## Fix backlog beyond the two allowed deferrals

### A01 P0 Deliver a backend acknowledgement before slow AI work

Reproduce with `validate belief`, `translate feature` or `answer site check by text` in the HTTP evidence. All exceed five seconds. Return a durable accepted message and acknowledgement, then publish the final answer through a resumable result/event mechanism. Alternatively meet the limit with a demonstrably bounded synchronous path. Preserve request-ID deduplication, version conflicts and retries. Avoid running known workflow answers through extraction and generative coaching.

Acceptance: measure header/first-message arrival and final-answer arrival separately; every tested first reply must be under five seconds, including cold requests and provider timeout. Report realistic concurrent-associate percentiles; do not use readiness timings as chat throughput proof.

### A02 P0 Finish channel-neutral text capture for installation and other input actions

Reproduce: `Site check`, then `Wall, socket checked, cable route clear, lift access checked, set top box checked, no specialist work`. After **22.685 seconds**, the answer is a missing-references fallback and `site` remains `{}`. `Confirm sale` similarly emits an input button without collecting the payable-amount confirmation in text. `Optional extras`, follow-up, expert creation and task updates also depend on form/action pathways by inspection.

Implement saved pending-input state with one missing site question at a time, safe cancellation and resumption. Collect optional choices, follow-up consent/time/owner, explicit sale confirmation and task evidence through the same backend text engine. Reuse existing deterministic validation; AI output must not execute an unconfirmed sale.

Acceptance: complete the entire associate journey through ordinary backend text without manually calling `/actions`, `/tasks`, `/requests`, or opening website forms. Inspection of final saved records must show all required evidence. Repeat declined consent, unknown specialist charge, customer leaving, demo unavailable and installation-delay branches.

### A03 P0 Add the active label-photo capability

`app/web/intelligence.py` explicitly tells coaching to request typed brand/model and not photos/scans. No active label recognition route is integrated into this journey. This is an input capability gap even before WhatsApp transport is added.

Acceptance: test label image upload against approved product identity, unclear/cropped/wrong labels, multiple models and unsupported specifications. Require confirmation when ambiguous; no inferred product facts. Explain the verified label for the saved home in three short lines. Do not classify photo support as merely provider integration.

### A04 P0 Restore and verify the voice runtime

Regression evidence: 13 failures and one error from missing FFmpeg; the Azure test module adds an import error for missing `azure`. The voice endpoint cannot establish usable capture/transcription in the environment tested.

Acceptance: provision declared Speech dependencies and FFmpeg in the actual contest runtime; run all voice regressions green, then use actual Hindi and Marathi recordings with the configured provider. Verify transcript review, translation, ambiguity, interruption, noise, retry and visit-note persistence. Keep this outside a text-only pass claim.

### A05 P1 Implement customer selection state in backend text

Reproduce `Customer list`, then `2` in the customer-navigation branch. The response is a website navigation button followed by a distance clarification; active customer does not switch. Date text queries return a count/link rather than paged serial entries.

Acceptance: show up to three customer entries, persist date and page state, accept serials only in selection mode, resume the selected conversation without changing its serial, and preserve normal numeric answers outside selection mode. Cover duplicate names, empty results, Today/Yesterday/ranges and admin owner context.

### A06 P1 Handle unknown product identity with the required missing-facts fallback

Reproduce `Explain model XYZ-UNKNOWN-999. Do not assume it is a known TV.` Actual reply: “I can help with TVs, store procedures and this customer's visit. What would you like to check?” Trace mode is `out_of_scope`; no model clarification or required missing-facts phrase is given. In contrast, missing cable length correctly returns “Not enough facts present.”

Acceptance: unknown IDs remain in-domain unresolved product identity; request a verified model/clear label and offer expert escalation, without recommending a substitute as if it were the same TV.

### A07 P1 Preserve language and intent through retrieval, commands and scoring

Marathi reproduction: switch to Marathi, then ask `ग्राहकाला क्रिकेटसाठी टीव्ही हवा आहे. कोणता प्रश्न विचारू?`. Actual answer is an English missing-facts fallback although the next missing question is known. Hindi belief correction is answered in Hindi but saved as `expert`, because coaching classification checks the English substring `customer says`. That also affects Validate evidence.

Acceptance: the same home, belief, feature, clarification and follow-up utterances in English, Hindi and Marathi take equivalent intent paths and retain the selected language. Evaluate unsupported-fact handling in every language. Use explicit semantic intent/evidence fields instead of English substring labels.

### A08 P1 Give itemised cost in chat and keep required and optional totals clear

After demo preference, actual chat gives “known solution cost” and site-check status rather than TV/delivery/installation/mount charges. Detailed quote API/PDF is itemised, but the documented floor conversation asks for that breakdown in chat as well.

Acceptance: render required charge lines over short message groups, identify every unknown charge, show separate optional selections and refresh the final amount on change. For the sampled finance case: required amount **INR 66,988**, upfront **4** + **12 x 5,582** + fee **999** = **INR 67,987**. The full-payment-only discount must remain excluded from finance.

### A09 P1 Make the coaching review evidence-specific

The successful structured journey receives internal 14/14, which is not a judge score. `domain.score()` awards two Validate/Translate points when any message of that type has sources; it does not verify the associate used the line or the customer understood it. The sampled Validate answer corrects immediately rather than explicitly acknowledging the partly correct belief. Review prompts can give generic “record the missing evidence” advice instead of one specific action.

Acceptance: tie scores to concrete saved evidence and relevant customer response; supported answers alone must not prove associate behavior. Preserve partial applicability but show a defensible final denominator and one specific next action. Cross-check with the seven-step 0-14 reference using an independent reviewer.

### A10 P2 Complete the shift-start floor conversation

`/api/shift` accepts `start` and `skip_practice`, directly saves TV and has no `TV` selection request. `Start shift` in a customer chat navigates to the website. Bootstrap contains the raw stock/offers/training data but this does not establish the required short conversational brief.

Acceptance: start outside a customer visit, select TV, receive concise current stock/offer changes and optional available video/question, then finish/skip practice and start or resume a customer. No fabricated daily changes.

### A11 P2 Reject conflicting reuse of a request ID

Supplemental replay probe submits `Hindi` twice with one ID, then `No consent` under the same ID. All return 200 with the original result. Deduplication prevents duplicate effects, but silently discarding different content makes delivery/retry defects difficult to diagnose.

Acceptance: bind request ID to original normalized payload and reject conflicting reuse, while exact retries keep returning the existing outcome.

## Final release gate

**Do not mark final acceptance complete with only WhatsApp and mock removal deferred yet.** Close A01-A09 and verify A10-A11 against the intended contest scope. Then rerun the audit against a fresh database and retain a green regression log.

The final independent acceptance run should demonstrate:

1. A complete text-only associate journey with no operator-injected structured recovery, including consent, recipient preview, explicit sale and owned follow-through.
2. A measured under-five-second first reply, three concise lines/buttons, grounded facts and uncertainty holds across normal and failure paths.
3. English, Hindi and Marathi equivalents; real audio and label images on the intended runtime.
4. Customer switching, duplicate names, date filters, expert interruption/reply, saved follow-up, reopened installation and working-check closure.
5. Correct amount/offer/stock changes under stale versions and concurrent attempts; exact-once retry behavior and provider-timeout recovery.
6. A rehearsed ten-minute scenario performed by someone unfamiliar with the implementation, followed by an independent seven-step review. Submission artifacts and actual WhatsApp proof remain outside this backend audit.

The existing saved-journey foundation is usable: structured safeguards, financial arithmetic, consented snapshots and follow-through gates held in the sampled cases. The remaining work is to make that foundation usable through the promised floor conversation and inputs, then prove it within the contest latency and live-test constraints.
