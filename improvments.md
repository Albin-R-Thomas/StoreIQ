# Store IQ associate journey review

## Implementation assessment — 1 November 2026

The original observations below are retained as historical evidence. The current
implementation supersedes the original statement that no fixes were made.

| Items | Assessment against the documented flows | Current disposition |
| --- | --- | --- |
| 1 | Valid: concise customer-specific recommendation reasons | Shortened reasons; B/C describe verified differences against A. |
| 2, 6 | Valid: explicit installation answers and invalidation | Separate required checks, Choose defaults, unknown holds, authoritative placement and refreshed evidence after home/TV changes. |
| 3 | Valid, but coverage cannot be invented | Approved editable descriptions, explicit absent-terms fallback, optional/required totals and relevance guidance. |
| 4 | Valid UI state defect by code inspection | Errors clear with customer/page context; late failures from an old context do not appear in the new one. Browser regression remains unverified. |
| 5 | Valid: commercial dependencies change independently | Quote fingerprints invalidate pre-sale previews/shares; purchased amounts stay frozen. |
| 7 | Valid: task dependencies must control closure | Pending/confirmed/problem reopening reopens the visit and invalidates downstream completion. |
| 8 | Valid: one match must remain usable | The match stays visible, with an explicit explanation and a single-TV physical-demo path. Comparison still requires two TVs. |
| 9 | Valid distinction between thread and decision | Thread resolution retains critical holds until attributed verification evidence is recorded. |
| 10 | Valid: follow-through needs reminders | Due task notifications are deduplicated by due cycle; internal/contact-consented tasks remain distinguished. |
| 11 | Valid for written coaching independently of voice | Added deterministic Hindi/Marathi guided prompts/buttons and principal form/error prompts. Whole-site translation and voice translation are not claimed. |
| 12 | Valid: the recipient/PDF transaction needs server enforcement | Expiring recipient-bound preview, generated PDF hash/version, consent/fingerprint check, one-use confirmation and share audit metadata. No external delivery. |
| 13 | Valid: documented continuation is the same thread | Identical resolved questions reopen with original ID/history and a fresh timer cycle. |
| 14 | Valid scope-consistency issue | Related queues follow customer filters; attempts follow associate/IST attempt dates; independent inbox/session scopes are labelled. |
| 15 | Valid: partial evidence and applicability differ | 0/1/2 evidence states, applicable denominator, feature-specific translation evidence and charge-aware Complete score. |
| 16 | Valid: a repeat demo needs a stated purpose | Saved customer-specific plan, repeat focus input, unavailable reason and verified alternative/expert recovery. |
| 17 | Backend observation valid; proposed backend redesign is not required by the web flow | Existing frontend already immediately says “Checking the latest details…” with role=status. Retained synchronous API and verified provider failure/retry behavior. No five-second completed-answer claim. |
| 18 | Valid: action label promised an unavailable edit | Honest Review details action plus an explicit owned purchase-correction request. Purchase amendment itself remains manager review; no silent stock/amount rewrite. |
| 19 | Valid content/rendering gaps | Site checks, serial, compared shortlist and contact owner in web/PDF; bundled open Devanagari font with shaping. Sample PDF rendered and inspected. |
| 20 | Valid: local rotation is insufficient for reload/device resume | Persisted answered/current feedback/finish/repeat session, used by the frontend. |
| 21 | Valid: structured price does not need a manual citation | Deterministic catalogue-price interruption preserves the pending home step. |
| 22 | Valid navigation intent | Deterministic date parsing with shared range validation and filtered-list navigation; reversed/ambiguous dates ask for correction. |
| 23 | Valid unavailable recovery suggestion | Coaching instructions explicitly limit recovery to typed brand/model and prohibit requesting photo/voice/WhatsApp input. |
| 24 | Valid: preferences are separate from a shortlist | Saved brand exclusion/maximum size, lower-range collection and stock-grounded regeneration with stale downstream evidence cleared. |

Validation: 38 local HTTP/domain regression tests; TypeScript/Vite production
build; Ruff checks with E501 excluded for existing long prose; 29 updated reviewer
observations in `output/improvements-review-evidence.json`; existing Postman AI
simulation covering actual SDK transport and injected 503 → application 502,
retaining one retryable message. No live model quality recheck was performed.

The browser host was unavailable and native Computer Use then stopped because
it could not reliably determine Edge's current URL. No successful browser
interaction is claimed. Meta/WhatsApp, voice translation, audio and OCR remain
deferred; legacy tests do not establish those integrations.

Reviewed 1 November 2026 against `docs/tv-store-associate-flows.md`.

## Scope and evidence

I acted through the backend HTTP routes using the actual FastAPI application and temporary SQLite databases. No frontend interaction, production customer edits, WhatsApp delivery or real payment was performed. Synthetic associate/admin accounts were used. The only persistence override points the application at a temporary database; workflow handlers were not stubbed. Clock-dependent probes age a saved task/request before exercising the HTTP handlers.

- Existing suite: `python -m unittest discover -s tests -v` — **29 tests passed**, exit 0. Some tests concern retired channel scaffolding; those do not establish current WhatsApp support.
- Additional reviewer probes: `python -m scripts.review_backend_flows` — **29 recorded observations**, exit 0; includes 18 training submissions covering all answers to all six questions. Evidence: `output/backend-review-evidence.json`. This is a diagnostic script, not a claim that every observation is correct behavior.
- Live configured AI: `python -m scripts.check_guided_chat --live` — passed natural extraction of seven home facts, grounded expert interruption and return to the saved step.
- Live configured AI: `python -m scripts.check_ai_simulation --live` — passed indexing, grounded coaching/comparison, context follow-up, unsupported-fact fallback and injection blocking. Comparison took **11.9 seconds**.
- Local Postman simulation: `python -m scripts.check_ai_simulation` — passed real SDK HTTP transport against the existing OpenAI stand-in; injected 503 produced application 502, retaining one retryable user message across retries. Simulation request events confirmed embeddings and Responses traffic. This verifies outage handling against the stand-in, not provider answer quality.
- Additional live conversational probes: `python -m scripts.review_live_coaching --live` — six HTTP 200 responses, exit 0, with answer-quality failures below. Inputs, full answers, sources and timings are in `output/live-review-evidence.json`.

The backend flows are promising, but I would fix quote freshness, assessment/site invalidation, task reopening and single-option dead ends before presenting this as the complete documented journey. Passing the existing tests does not cover these transitions.

## Original observations, retained

1. **Shorten recommendations.** They repeat several specifications for each TV. Give one main reason and one trade-off per option. **Reproduced in backend:** a bright-room cricket/side-seat customer receives three long lines repeating refresh rate, nits and viewing angle. B/C do not clearly explain their improvement or compromise relative to A. Fix `domain.recommendation_reason` and the recommendation prompt; preserve detailed specs in comparison.
2. **Make installation confirmation explicit.** The site form defaults to “No—standard installation confirmed.” Start with “Choose” so associates must confirm it. **User-reported frontend finding, not rechecked through UI.** Backend rejects a missing specialist value, but accepts `specialist=no` with the five-character note `maybe`, immediately setting `site.confirmed=true`. Require individual answers for power, cable route, wall/access, devices and specialist needs, including Unknown; unknown material details should keep finalisation pending.
3. **Improve optional-extra explanations.** “Demo coverage” does not explain what the protection plan covers. **Original UI wording not rechecked.** Backend quote names a “2-year protection plan” with its price but does not supply coverage, exclusions, provider or claim procedure. Store approved descriptions, show relevance and separate required/optional totals, and say coverage is not confirmed when absent. Add/remove recalculation itself passed.
4. **Clear old errors when navigating.** A previous customer’s cost error remained visible on unrelated overview and training screens. **User-reported frontend finding; backend-only testing cannot verify navigation state.** Scope errors to customer/action and clear them when the context changes; verify separately in UI regression testing.

## Additional findings and concrete fixes

### 5. P1 — Commercial edits do not invalidate shared quotes

**Reproduction:** create a ready customer; consent; POST `/api/customers/{id}/share`; admin increases the preferred product price by ₹1,234; GET current summary and `/api/shared/{token}`. The shared total stayed ₹63,988, current total became ₹65,222, but `outdated` remained `false`.

**Impact:** an associate/customer can trust an old pre-sale price as current. Staleness only compares customer versions, while commercial records can change independently.

**Fix:** capture product/commercial/offer versions in the quote fingerprint and PDF/share snapshot. Mark pre-sale snapshots outdated when any dependency changes. Preserve frozen completed-purchase totals.

### 6. P1 — Home corrections retain incompatible confirmed installation details

**Reproduction:** complete a wall site check; edit home placement to Table; reconfirm and demo again. `home.placement=Table`, `site.placement=Wall`, `site.confirmed=true`, and the quote has no missing details. The old wall mount remains chargeable.

**Fix:** invalidate site confirmation when placement, relevant home needs or selected TV changes; reconcile placement in one authoritative record. Require refreshed installation answers and reconfirm changed costs before payment/sale.

### 7. P1 — A reopened installation can leave the customer closed

**Reproduction:** complete delivery, installation and working check; POST the installation task back to `pending`. HTTP 200; customer stage stays `closed` despite pending installation. The existing handler reopens on `problem`, not other unfinished statuses.

**Fix:** derive closure from current task dependencies. Reopening delivery/installation should reopen the customer and invalidate dependent completion evidence where appropriate. Check `pending`, `confirmed` and `problem` transitions, not just the happy sequence.

### 8. P1 — One suitable TV creates an unavoidable demo/payment dead end

**Reproduction:** budget ₹30,000 returns only `lg-u43`. The flow hides the model behind “There are fewer than two TVs in this shortlist.” Recording its physical demo returns 409 because demo requires at least two TVs. Offers/payment consequently remain inaccessible.

**Fix:** show the one verified match and explain why there are fewer options, as the document requires. Support an evidenced single-TV physical demo without pretending a comparison occurred; alternatively explicitly save/route the exception. Never require an over-budget second TV to continue.

### 9. P1 — Resolving a blocker does not require evidence that its underlying uncertainty is settled

**Reproduction:** create a blocking request about unknown compatibility; payment is blocked. `expert_resolved` resolves the unanswered request without evidence; payment then succeeds.

The document permits the associate to resolve questions, so the button itself is valid. **The gap is treating resolution as proof of compatibility/cost/finance certainty.**

**Fix:** separate thread resolution from the affected decision's confirmation. Record the approved answer/evidence or verified alternative before clearing a critical hold. Keep unsupported amounts and compatibility pending even if a thread is dismissed.

### 10. P1 — Overdue delivery/follow-up tasks have no notification mechanism

**Reproduction:** save an internal follow-up, age its due time ten minutes into the past, trigger bootstrap/reminder processing twice. No notification is created. Code inspection confirms the scheduled reminder loop processes expert requests only.

**Fix:** process due delivery, installation, working checks and agreed follow-up updates; notify the owned queue once per cycle, retain unresolved tasks, and distinguish internal-only tasks from consented customer contact. This needs a scheduler-level test as well as API verification.

### 11. P2 — Guided coaching ignores Hindi/Marathi language selections

**Reproduction:** language actions save Hindi and Marathi, but the full-cost guided lines remain entirely English. The fixed flow strings do not use `customer.language`.

**Fix:** localise all deterministic questions, validation errors, buttons, cost/handover/task and review prompts. Preserve model names and amounts. Live model translation alone cannot translate the main journey.

### 12. P2 — Sharing does not enforce the documented recipient/PDF preview transaction

**Reproduction:** consent plus `{version, action:"share", data:{confirmed:true}}` creates a link with HTTP 201 without a recipient or prior PDF generation.

**Fix:** persist an expiring preview tied to recipient, consent purpose, quote fingerprint and PDF version; confirm that exact preview, recording recipient/time/version. Cancel should create no share. Current link creation is a useful internal snapshot, but does not establish the documented simulated sharing flow. Consent refusal/revocation did pass existing tests.

### 13. P2 — “Ask admin” after resolution creates a different request

**Reproduction:** create request, resolve it, then submit the same customer/question through POST `/api/requests`. A different ID/number is created. Open-request deduplication works; resolved-request continuation does not.

**Fix:** reuse/reopen the resolved thread for the documented “Ask admin” continuation and start a fresh timer cycle. Preserve original history, sources and attribution. Explicit new-question creation can remain separate.

### 14. P2 — Admin filters do not consistently scope related data

**Reproduction:** `/api/bootstrap?associate=associate-2` filters customers to associate 2 but returns associate 1's tasks and training attempts. A date filter with zero matching customers still returns four tasks in the probe.

**Fix:** apply explicit associate/date semantics to training progress, task summaries and history data, or return independently labelled scopes. The current response can produce misleading filtered manager totals. This is a scope consistency issue, not a demonstrated associate ownership leak.

### 15. P2 — Coaching score does not implement partial/applicable scoring

**Reproduction:** ending a partially completed visit shows `6/14`, with unperformed stages pending. The score function only awards 0 or 2, never 1; any sourced assistant answer can satisfy Translate, and site confirmation alone satisfies Complete even if a specialist amount is unknown.

**Fix:** define evidence for each 0/1/2 state, compute an applicable denominator for unfinished visits, and distinguish missing required evidence from not-yet-due work. Do not award feature translation from an unrelated sourced lookup or complete cost while charges remain unknown. Keep final /14 only when applicable.

### 16. P2 — Demo instructions are generic rather than customer-specific

**Observed backend behavior:** fixed instructions always request cricket/movie clips, daylight reflections and side seats, even when home answers are Unknown. There is no different saved plan for “Need another demo”; it reruns the same action.

**Fix:** name the selected pair and prioritise this customer's unresolved difference: dialogue, gaming, reflection, motion or viewing angle. Ask what remains unclear for another demo. Record what was unavailable and suggest a verified display alternative.

### 17. P2 — Slow AI replies lack a backend acknowledgement

**Reproduction:** sampled live comparison took 11.9 seconds. The HTTP handler waits for the complete model answer and exposes no interim “Checking the latest details” response/event. This exceeds the document's five-second first-reply target.

**Fix:** return a saved pending operation/acknowledgement promptly, then stream or poll for the answer; persist retry/failure status without duplicating messages. Backend-only testing does not establish whether the UI already displays a temporary loading indicator.

### 18. P2 — Handover offers “Edit details” after freezing every editable purchase field

**Evidence:** happy sale probe confirms purchase freezing; existing tests confirm home edits return 409 after sale. `flow.build` still presents “Edit details” in the consent step, but it only navigates to summary. `domain.act` rejects site, extras, preferred TV and payment changes after sale.

**Fix:** define a controlled amendment/reconfirmation flow with stock and quote audit handling, or change the action to an honest “Review details” and expose an explicit correction route. The documented button promises changes, not just navigation.

### 19. P2 — Summary contract/PDF omit useful documented handover information

**Evidence:** inspect actual summary payload plus PDF generator: quote contains home, compared models, preferred product, demo reason, charges and tasks, but omits the saved detailed site assessment from the summary contract. The generated PDF does not print the permanent customer serial or compared-TV list and cannot render Indic text with its built-in font.

**Fix:** include serial, compared options, site needs and customer-facing contact owner in both outputs; embed a Unicode font for names/home text. Keep internal notes/coaching private. PDF endpoint validity passed; visual layout and Indic rendering were not tested through a PDF viewer in this backend review.

### 20. P2 — Training persistence covers answers, not the documented resumable practice session

**Evidence:** all 18 training submissions produce correct answer/feedback records; repeated answers are accepted. Backend exposes attempts but no active question, finish/repeat cycle, exhausted set or unanswered question state.

**Fix:** persist an associate practice session with question rotation, current unanswered question and finish/repeat transitions. Verify resume across devices/reload and that practice cannot alter customer scores. Frontend may implement some rotation locally; this review does not certify it.

### 21. P1 — A known early price question incorrectly returns missing facts

**Live reproduction:** “What is the current price of Samsung Vision Q55? The customer asked price before answering the home questions.” The API returned “Not enough facts present. The answer did not include supporting references. Ask an expert to confirm.” The approved structured catalogue contains the price ₹64,990. Home stayed empty and the conversation entered expert mode rather than giving the price then asking the next home question.

**Fix:** answer prices deterministically from the current structured catalogue with an appropriate structured-data reference. Do not require a RAG document citation for a value deliberately excluded from the embedding index. Preserve the home question after the price interruption. This is one sampled live failure; add repeated paraphrase checks.

### 22. P2 — Natural-language customer date searches are treated as out of scope

**Live reproduction:** “Customers from 5 Nov 2026 to 1 Nov 2026” receives “I can help with TVs, store procedures and this customer's visit. What would you like to check?” instead of asking to correct the reversed dates. Explicit bootstrap date parameters correctly reject the same invalid ordering.

**Fix:** recognise customer-list/date intents before model routing and use the same validated date-filter service as the list API. Do not send a navigation/filter request through feature explanation. Also test Yesterday, ambiguous dates, empty results and Change dates.

### 23. P2 — Model replies advertise unavailable photo input

**Live reproduction:** the unknown-model response correctly declines to invent specifications, then asks for “a photo of its specification label,” although the mounted application supports text only.

**Fix:** pass current channel capabilities into coaching instructions and ask for a typed brand/model until uploads/OCR exist. The missing-fact fallback itself passed; the offered recovery action is unusable in this release.

### 24. P2 — Conversational preference changes do not update saved preferences

**Live probe:** after discussing Samsung Vision Q55, “Change options to a smaller size from another brand” produced a missing-facts answer. No preference was saved; the old feature-explanation flow remained visible. This probe was before home confirmation, so it does not establish all post-recommendation behavior, but the known preference should still be remembered and acknowledged.

**Evidence from contract inspection:** saved home fields contain no brand/size constraints; the Change options action only accepts product IDs. There is no deterministic natural-language preference-change handler.

**Fix:** store brand/size constraints independently from an explicit shortlist, collect missing home details, and regenerate stock-grounded options when ready. Test “lower range,” “other brand,” “smaller size” both before and after recommendation, with demo/payment invalidation after changed selections.

## Coverage against the complete flow document

| Documented area | Backend interaction and result |
| --- | --- |
| Login/roles | Existing tests: correct role, cross-associate access denied, admin endpoint denied to associate, foreign-origin write denied. Passwordless admin escalation does not occur. |
| 1. Shift and training | Start/skip succeed, invalid shift rejects; all question answers exercised; session lifecycle gap #20. Video absence/current frontend rotation not verified. |
| 2. New/resume customer | Separate IDs, permanent increasing serials, duplicate names, saved GET history; new record does not delete prior records. Voice name matching excluded. |
| Lists/date filters | Invalid/reversed dates reject; custom IST boundary and returning activity probe passes, appears once, history retained. Admin scoping gap #14. Website pagination is outside backend evidence. |
| 3. Home assessment | Seven answers, Unknown skip, complete confirmation, edit invalidation of demo/payment; retained site gap #6. |
| 4. Customer belief | Additional live conversational probe; saved step preservation covered by expert interruption test. |
| 5. Labels/features | Typed known/unknown model probes; photo OCR is absent from the current text-only API. |
| 6. Recommendations | Three options, low/no-match budgets, Unknown details, current stock; concise reasons gap #1 and one-option dead end #8. |
| 7. Demo | Start/read does not complete; preference plus reason completes; unavailable retains incomplete status and blocks offers; generic follow-up gap #16. |
| 8. Full cost | Itemised arithmetic and extras add/remove pass; unknown specialist holds total/payment; admin-confirmed specialist charge restores total. Explicit site evidence gap #2. |
| 9. Offers/payment | Early payment and incomplete demo reject; eligible offer, full payment, finance arithmetic tested; finance does not combine offer; payment preference does not sell. Early-price conversational probe included separately. |
| 10. Later/out of stock | Consent/no-consent follow-up, owner and future time; stock disappearance blocks sale and offers alternative/follow-up actions; due reminders gap #10. |
| 11. Handover | Explicit matching total, sale once, three separately owned pending tasks, frozen quote, consent refusal; correction gap #18. |
| 12. Follow-through | Working check before installation rejects; ordered task completion closes; issue pathway and pending reopening inspected; closure regression #7. |
| 13. Review | End/resume preserves stage and tasks; score generated; partial/applicable evidence gap #15. |
| 14. Anywhere actions | Language, note/history, pause/resume, expert interruption, new-customer separation; fixed prompt language gap #11. Voice ambiguity and voice notes excluded. |
| Comparison | Live grounded two-TV verdict with home context; duplicate/unknown model validation in implementation; one-item comparison rejects. Opening comparison does not count as physical demo. |
| Expert/admin | Grounded supported answer, missing-fact exact fallback, injection blocked; request dedup, reply attribution, notifications, follow-up, reminder/escalation once after aged cycle covered by existing tests. Reopening/blocker gaps #9/#13. No WhatsApp delivery claim. |
| Summary/PDF/share | Pre-sale quote label, PDF signature, consent gating, snapshot, customer-edit staleness, revocation pass; dependency freshness/preview/content gaps #5/#12/#19. |

## Scope decisions, not defects in the current release

The current README explicitly describes a **text-only web application**. WhatsApp integration, voice capture/transcription, label photos/OCR, cross-channel resume, WhatsApp reply retry/delivery receipts and return-to-WhatsApp actions therefore cannot be tested on this release. Track these as deferred document requirements, not fabricated failures of an integration that has not been built. The repository's legacy routes/tests do not prove the current app supports them.

No frontend was used, as requested. Visual responsiveness, focus/accessibility, stale UI errors, downloads through a browser and actual screen navigation still require a separate UI review. The backend coverage above exercises every numbered flow's available route, but does not claim exhaustive coverage of every input combination, concurrency schedule or language output. No application fixes were made in this review.
