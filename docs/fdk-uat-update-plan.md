# Store IQ updates for FDK UAT and contest readiness

Review date: 3 November 2026. Internal confidential use only.

Store IQ has a substantial working website journey, but the active application does not yet meet the contest's WhatsApp, voice and photo requirements. Its product and commercial records are synthetic. The supplied FDK v1.9.5 reference provides two useful read APIs, not a complete store operations integration. The highest priority is to connect the existing journey to an approved test WhatsApp number, add voice and label-photo handling, and replace synthetic facts only where approved data supports them.

This is an implementation plan. It does not change application behavior. Keep the existing assessment, physical-demo, explicit-sale, consent and working-check safeguards as integrations are added.

## Evidence and scope

Primary inputs:

- [Requested journey](tv-store-associate-flows.md), including its ten-minute demo story.
- [FDK method reference](../FDK_Method_Reference_v1.9.5_UAT.docx), sections 1 and 2 and UAT environment URLs.
- [Contest brief](../6_Reliance_Digital_Store_IQ_Contest_28Oct2026.pdf), pages 1 and 2.
- [Store visit findings](<../Store_Visit_Findings_Reference_27Oct2026 (1).pdf>), pages 1 and 2.
- Active entry point, web API, domain rules, seed data, AI/retrieval code, frontend and retained adapter scaffold listed below.
- [Existing validation](validation.md) and [saved explicit Basic authentication checks](evidence/fdk-uat-explicit-basic-recheck.json).

Code inspection establishes implemented behavior; it does not establish the current deployed database contents or a successful live WhatsApp journey. Existing validation reports local and sampled live AI checks. Those tests were not rerun for this documentation review.

The supplied authenticated product GET was also checked during this review. The runtime reported `2026-11-02T18:43:52Z`; it returned **403**, `text/html`, rather than a JSON product response. This agrees with the saved evidence. Preserve that recorded timestamp separately from this document's review date. No successful FDK response schema has been verified here, and the promotion endpoint was not rechecked in this pass.

## Current architecture

| Component | Current role | Consequence for the update |
| --- | --- | --- |
| `app/main.py` | Serves React assets and mounts `app.web.api`; starts persisted reminder processing | This is the deployed application to extend |
| `frontend/src` | React and TypeScript workspace calling same-origin `/api` | Retain detailed catalogue, comparison, training, summary and manager views |
| `app/web/store.py`, `seed.py` | Durable SQLite records initialized with synthetic products, commercial facts, accounts and knowledge | Existing records are local data, not FDK responses |
| `app/web/domain.py`, `actions.py`, `flow.py` | Deterministic journey rules, validated actions, quote arithmetic, recommendations and prompts | Reuse these rules across channels rather than creating a second journey |
| `app/web/intelligence.py` | OpenAI structured extraction and answers; BM25 plus vector retrieval | Active AI is a real provider integration when configured; facts are still synthetic |
| `app/legacy.py` | Separate, explicitly unserved regression harness for older adapters | Passing its tests does not demonstrate active website or WhatsApp integration |
| `app/meta`, `app/recordings`, `app/catalog` | Retained channel/transcription/catalogue scaffold | These modules are not wired into the active web journey |

The architecture document records an earlier deliberate web-only and text-only scope. Contest readiness requires changing that scope explicitly and updating the documentation once the new channels actually work.

## What is mocked or simulated

| Area | Current implementation and evidence | What must change |
| --- | --- | --- |
| TV catalogue | Eight seeded TVs with synthetic names/specifications, prices, stock and arrival dates; `seed.py` sets `mock=True` | Import approved product records with stable external IDs and provenance; preserve fixtures as an explicitly selected demo dataset |
| Product editing | `api.py` Product schema requires complete TV facts and `save_admin` forces product `mock=True` | Separate imported facts, approved manual enrichment and fixtures; stop marking every product synthetic once real imports exist |
| Stock | Seeded integer quantities; sale decrements local SQLite stock | No live store inventory connection. Keep local test allocation separate from external availability |
| Offers | Two seeded dated offers, brand/size filters and fixed rupee discounts | Add a promotion adapter; current offer schema cannot represent general FDK promotion rules |
| Finance and charges | Editable synthetic delivery, installation, mounting, extras and a zero-APR finance plan | Obtain approved test terms; neither supplied FDK method supplies these contracts |
| Sale and payment | Explicit synthetic sale, frozen purchase quote and local stock change; payment choice is a preference | No payment capture, order creation or finance approval. Continue to label these as test actions |
| Delivery and installation | Real persisted internal tasks, owner, due time and working-check evidence | These are local workflow records, not resQ jobs, carrier tracking or confirmed appointments |
| Summary sharing | Real PDF and expiring, revocable snapshot links; recipient/preview/consent workflow | No external customer message is sent by the active application |
| Expert support | Real local requests, attributed admin replies, notifications and reminder cycles | No WhatsApp notification delivery; one seeded admin means escalation uses a queue |
| Accounts and training | Synthetic users, visitors, six questions and four procedure documents | Keep all people and recipients test-only; add an approved short shift video |
| Active AI and RAG | Configured OpenAI SDK calls, embeddings, structured outputs, hybrid retrieval and provider-error handling | Do not describe this as a fixed mock chatbot. Review actual factual inputs and language quality |
| Postman AI stand-in | `postman/mocks/openai/default.js` returns constant vectors, fixed structured answers, null home extraction and an injected 503 | Useful for SDK transport/schema/error checks; cannot establish recommendation or model quality |
| Legacy mock AI | `app/ai/provider.py` has `MockAIProvider`; old `AI_PROVIDER` switch belongs to the scaffold | Do not confuse this with the active web AI path |
| Legacy WhatsApp | `MetaClient` mock mode returns a fabricated message ID without HTTP; live branch sends text only | A live branch existing in a file is not an end-to-end channel integration |
| Legacy incoming webhook | `app/meta/router.py` validates signatures and records inbox events using the PostgreSQL model | It is not mounted by `app.main`; inbox storage alone does not run the web journey |
| Legacy audio | `PendingTranscriber` raises an integration-not-configured error; `mock_recording_text` substitutes typed text | Add actual media download and transcription; mock recording tests are not voice evidence |
| Legacy catalogue | `EmptyCatalogProvider` returns `status=unavailable` and empty lists | There is no implemented FDK client here; simply replacing this unused provider will not update web records |
| Label photos | No active upload, OCR/vision, product matching or confirmation path | Implement the translate flow with an explicit model-confirmation step |

## Contest gaps by journey

| Journey | Existing foundation | Required update and observable completion |
| --- | --- | --- |
| Before shift | Stock/offer brief and persisted practice attempts | Start from WhatsApp; use approved current facts, show a short video and one question. Website can retain extended practice |
| Assess | Text home extraction, one missing question, home confirmation, permanent customer serials | Send a real test voice note; confirm transcript/home facts and resume the same customer on the website |
| Validate | Grounded text coaching and missing-fact fallback | Demonstrate a polite confirmation and correction for “all 4K TVs are the same,” tied to the saved home |
| Translate | Typed feature/model explanation | Send a real label photo; match an approved product, ask if uncertain, and explain only supported facts for this home |
| Recommend and demonstrate | Up to three local in-stock options, reasons, comparison and physical-demo evidence | Use verified availability and nullable specs; send floor-sized replies and record preferred TV plus reason after the actual demo |
| Complete | Itemised quote, optional extras, site check and unknown-charge blocking | Use approved charges; show known subtotal and pending costs without claiming a final total |
| Close | Assessment/demo gates, dated local offers, explicit payment choice and sale | Map promotions safely, prevent double discounts and reconfirm changing facts; show full approved finance cost in one sentence |
| Follow through | Consent, PDF snapshots, owned delivery/installation/working-check tasks | Deliver only to approved test recipients; expose real channel delivery state; retain separate working check after installation |
| Review | Evidence-based seven-step scoring | Show score out of 14 and one actionable improvement in WhatsApp; preserve evidence in manager view |
| Extra points | English/Hindi/Marathi support, admin filters, expert workflow, typed visit notes | Verify Hindi and Marathi with actual users, deliver expert replies through both channels, save a real voice visit log |

The contest assigns demo points to WhatsApp completion (25), required steps with reasons (25), floor usability (20), correctness/safety (20) and extras (10). Demo and later live test each contribute 50% to judging. A polished website alone leaves a central judging requirement unmet.

## What the FDK reference supports

### Product listing

`GET /service/application/catalog/v1.0/products`

Documented query parameters: `q`, `f`, `filters`, `sort_on`, `page_id`, `page_size`, `page_no`, `page_type`. The reference describes cursor paging as the default. Choose one paging mode explicitly; follow returned metadata and prevent repeated-cursor loops. Discover supported filter and sort values from the response rather than inventing category names or sort enums.

The sample request uses `page_size=2&filters=true`. Two returned products are only a sample page, not the complete TV assortment. Confirm the TV department/category filter from actual UAT data, then process all required pages.

| Documented FDK field | Proposed Store IQ mapping | Important constraint |
| --- | --- | --- |
| `uid`, `slug`, `item_code` | External product identity, promotion lookup and label matching | Preserve all identifiers; do not key imports by display name |
| `name`, `brand.name`, `categories` | Display model/brand and approved TV classification | Do not infer category merely from a search hit |
| `price.effective`, `price.marked`, `price.selling` | Structured monetary values and display price | These are min/max blocks. Confirm variant and price semantics before producing a single payable amount |
| Currency fields | Currency-aware amount | Current quote assumes integer INR; reject unsupported currencies and handle decimal units explicitly |
| `attributes`, `highlights`, `short_description` | Approved specifications and explanation evidence | Attribute keys and units remain unverified. Missing nits, native Hz or HDMI count must stay unknown |
| `medias / images` | Actual approved product imagery | Reference uses alternate labels; confirm real JSON shape before choosing a parser |
| `sellable`, `sizes`, `variants` | Listing availability and variant selection | `sellable=true` does not establish on-hand stock at a physical store or a quantity |
| `filters`, `sort_on`, `page` | Catalogue browsing and pagination | Preserve metadata; contract-check actual response fields |

### Promotion listing

`GET /service/application/cart/v1.0/available-promotions`

Documented parameters: `slug`, `page_size`, `promotion_group`, `store_id`, `cart_type`. Response: `available_promotions[]`, including `id`, `buy_rules`, `offer_text`, `promotion_type`, `promotion_name`, `promotion_group`, `valid_till`, `discount_rules`, `free_gift_items`, `description`.

Store the provider rule structure and terms. A returned promotion is an available offer to evaluate, not proof of eligibility or a successfully applied cart discount. The reference does not define the nested rule semantics sufficiently to implement every discount type safely. A free gift is not a rupee price reduction. `valid_till` is a timestamp; preserve its timezone rather than truncating it to a date.

Do not translate every promotion into the current `discount: int`, brand and minimum-size model. Do not apply the largest textual offer as a guaranteed discount. Establish store/product/cart context and confirmed rule semantics first. Unsupported rules can be displayed after the gate with “Eligibility not confirmed,” without changing the payable total.

### Capabilities still requiring approved data or another contract

- Physical store stock quantities, display/demo availability, reservation and expected arrivals.
- Complete TV specifications when absent from listing attributes.
- Authoritative cart pricing, discount application, stacking, bank eligibility and exchange valuation.
- Finance approval, interest-bearing EMI calculations, fees, taxes and lender terms.
- Installation/site charges, protection coverage, accessory compatibility and resQ job integration.
- Order creation, payment, fulfilment tracking and confirmed appointments.
- WhatsApp transport, transcription and label recognition.

These are gaps in the supplied two-method reference, not claims that the wider FDK platform lacks the capabilities. Keep approved test fixtures where permitted and label their source; never fill a missing field with a plausible specification or zero charge.

## Access and integration design

### Verified production storefront request

A subsequently supplied GET to `https://www.reliancedigital.in/ext/raven-api/catalog/v1.0/products?page_id=%2A&page_size=12&q=tv` returned **200**, `application/json`, with **12 items** and no redirects from this runtime. Top-level fields were `items`, `filters`, `page`, `sort_on`, `smartFilters` and `meta`. Product records included identity, attributes, categories, sellable status, brand, media, price and variants. This establishes a successful catalogue read for this request.

This is a different production storefront host and `/ext/raven-api` route, using a different credential from the supplied UAT application pair. The request also supplied cookies, SDK/date/signature and browser headers. Their individual necessity and signature renewal remain unverified; a successful replay does not establish a durable integration contract or working UAT access. No credentials or cookies are recorded here. Keep contest integration approval and test-data rules distinct from this read-only production catalogue check.

### Authentication matrix follow up

The [expanded live matrix](evidence/fdk-auth-matrix-expanded.json) subsequently completed all **144 cases**: 48 each on the supplied storefront, platform and partners origins, covering both path endings and 24 authentication/header/query configurations. All 144 returned HTTP 403 HTML; none returned JSON or the required `items` array. No working curl was identified. The results do not establish that either portal origin is a valid REST base or that the application credentials are invalid. Further integration needs the UAT owner's confirmed API origin, authentication requirements and access context rather than a claimed successful permutation.

The supplied application ID and token support two source-backed candidates: Basic with Base64 of `application_id:application_token`, as used by the [Fynd application Postman collection](https://www.postman.com/fynd-platform/fynd-api/collection/wjhz3f2/fynd-platform-s-application-side-apis-v2-0-0), and Bearer with the same encoded pair, as described by the [current headless authentication guide](https://docs.fynd.com/partners/commerce/headless/authentication/). These sources describe different contexts; neither establishes which scheme the supplied UAT route accepts.

The [six-case live matrix](evidence/fdk-auth-matrix.json) tested no authentication, Basic and encoded-pair Bearer, each with and without a trailing slash on the product path. Every case returned 403 HTML with no redirect. This uniform result does not validate or invalidate the credentials and is consistent with rejection before application authentication; the rejecting layer needs confirmation. No JSON catalogue payload was obtained.

Run `python scripts/check_fdk_auth.py` on the computer where Postman runs to repeat these cases. It prompts for the application ID and masks token entry, or reads `FDK_APPLICATION_ID` and `FDK_APPLICATION_TOKEN`. Optional `--output <path>` saves status/shape diagnostics without saving request credentials or response bodies. It uses Windows curl with certificate validation and best-effort revocation checking, and does not follow redirects.

In Postman, use either Basic Auth with ID as username and token as password, or Bearer Token with Base64 of `ID:token`. Set only one Authorization header. Keep redirects disabled initially so routing failures remain visible. A raw application token is not the encoded-pair Bearer value described by the guide. Platform OAuth requires separate client credentials; this application pair alone does not establish those credentials. Do not send these UAT credentials to guessed production hosts.

The subsequently supplied `image.png` confirms that Postman shows **200 OK** with an **HTML storefront error page**, including “Oops! The page was not found.” This is not the documented catalogue JSON response. The screenshot establishes a successful HTTP response carrying a page-not-found UI, not successful product API access. The correct API routing/base URL still needs confirmation; the screenshot alone does not establish the cause or whether a redirect occurred.

Use the supplied UAT host and Basic authentication scheme for the authorized catalogue check. Keep the credential server-side in a secret environment value; never copy it into frontend code, this document or committed Postman environments. Do not infer a different authentication scheme from the SDK version.

The 403 HTML response means this agent runtime obtained no catalogue payload. Existing saved checks also show 403 HTML for promotions. The user reports that the same authenticated product request with `page_size=1&filters=true` returns HTTP 200 in Postman. An agent-runtime retry with those exact query parameters still returned 403 HTML. Access therefore differs between the observed clients; UAT must not be described as universally inaccessible. The user's description of the successful body as HTML still needs clarification: a usable product contract requires JSON containing `items`, not merely HTTP 200. Compare Postman's response content type, final URL, proxy/VPN configuration, cookies and effective request headers with the backend runtime. Confirm application permissions or edge policy with the UAT owner if those differences do not explain the result. Provide only redacted diagnostics privately. Do not disable TLS validation to address an HTTP access denial.

Recommended implementation:

1. Add a backend FDK client and explicit configuration for UAT base URL and auth. Give reads bounded timeouts, JSON/content-type/schema checks and limited retries for transient failures. Treat access denial separately from an empty successful list.
2. Normalize responses into source-aware records containing external identity, variant, currency, source type, fetch time, approval and freshness state. Keep raw provider data separate from the public response.
3. Refresh outside SQLite write transactions, validate the batch, then publish atomically. A failed page must not publish a misleading partial assortment. Deactivate missing products only after a successful complete refresh.
4. Use nullable TV facts and explicit availability states such as `unknown`, `listing_sellable`, `store_confirmed` and `out_of_stock`. Require confirmed store availability when promising an in-stock recommendation.
5. Preserve stable product IDs referenced by customer selections, citations, tasks and frozen purchase quotes. Keep imported source fields separate from approved manual enrichment and local test allocation.
6. Read normalized facts through the active web services. Update bootstrap, recommendations, comparison, quote, shift brief and retrieval together. Do not implement only the unserved catalogue provider.
7. Recheck price, availability, offer expiry and terms before finalization. Include source changes in quote fingerprints so existing previews become stale. Preserve frozen test purchases as historical snapshots.
8. Retain the last successful snapshot with a visible stale warning when access fails. Disable actions needing fresh commercial confirmation; never silently switch from UAT to synthetic prices or stock.

## Code updates that matter most

| Files or boundary | Required work |
| --- | --- |
| `app/web/api.py` Product/Offer/Commercial models | Allow unknown imported specs and source metadata; support range prices and typed promotion rules without weakening input validation |
| `app/web/api.py` bootstrap | Currently returns all local offers to associates before gates. Return only permitted promotional data and audit all response surfaces |
| `app/web/domain.py` `eligible_offers`, `quote` | Replace fixture-specific eligibility/max-discount logic only after rule semantics are known; maintain deterministic totals and unknown-charge blocking |
| `app/web/domain.py` recommendations/reasons | Current ranking indexes numeric Hz/nits and stock directly. Handle unknown attributes, currency, variant and availability without crashes or invented reasons |
| `app/web/domain.py` sale action | Keep local synthetic decrement separate from imported inventory; a local change must never imply an upstream reservation/order |
| `app/web/intelligence.py` | Replace hardcoded synthetic-only source labels/prompts with actual source status. Index only verified stable facts; continue supplying commercial data separately |
| `frontend/src/catalogue.tsx`, comparison and summary views | Display unknown/range values, actual imagery, source/freshness and availability accurately; audit promotional labels before assessment/demo |
| `app/main.py` and new channel adapter | Mount approved webhook endpoints and connect them to the same SQLite journey; retain authentication and ownership boundaries |
| `app/meta/*` and channel persistence | Adapt useful signature/send logic; add inbox/outbox processing, replay deduplication, interactive replies and delivery status. Existing PostgreSQL scaffold cannot simply be mounted against the web SQLite schema |
| Audio and image handlers | Download authorized test media, transcribe/recognize, confirm uncertain results, retain linkage to the correct visit and provide typed fallback |
| Summary and expert delivery | Reuse consent/version checks; add test-recipient enforcement, delivery status and retry without duplicated business actions |
| `app/main.py` browser policy | Current policy disables microphone/camera and limits images to self/data. If web capture or remote images are added, adjust narrowly and validate upload/body limits; WhatsApp media does not require browser capture |
| API artifacts and project docs | Regenerate active OpenAPI after implementation; update architecture, web API contract, README and validation to match actual supported channels and sources |

Keep model output advisory. Transcript, OCR or chat text must never directly mark a demo, sale, consent or installation complete.

## Priority plan before submission

The brief sets submission for **6 November at 18:00**, demos on **9 November**, and a later store test after Diwali. Confirm the organizer's submission timezone; it is not specified in the brief. The order below is a recommendation, not an estimate that access approval will arrive in time.

### P0 establish the test channel and approved facts

- Obtain the approved WhatsApp test number and recipient allowlist; route text through the existing journey and prove cross-channel resume.
- Resolve UAT access in parallel with channel setup. Obtain approved TV and commercial test data for capabilities outside the two documented methods.
- Fix offer leakage from bootstrap and other associate-facing surfaces. Price questions may be answered honestly, but proactive promotions must remain gated.
- Add an acknowledgement for slow work and measure user-visible first reply below five seconds. Historical validation records an 11.2-second comparison response, so the current synchronous path does not establish that target.

Completion: an approved test associate starts a visit on WhatsApp, gets a prompt, resumes it on the website and cannot obtain premature promotional closing content.

### P0 complete voice photo and the sale journey

- Real voice note to confirmed home card; real photo to confirmed model and grounded explanation.
- Three supported TV options with reasons, physical-demo preference/reason, site check, itemised cost and approved offer/payment terms.
- Explicit test sale, consented test summary delivery and independently owned delivery, installation and working-check tasks.
- Every floor message rendered as at most three lines and three buttons, including failure and expert-wait responses. Persist long details for website access.

Completion: the ten-minute TV story runs on the test WhatsApp number without manual database changes or scripted claims of physical completion.

### P1 improve live test performance

- Demonstrate Hindi and Marathi on voice, transcription, prompts and corrections; test product names and code-switching.
- Reuse the manager view and expert workflow; send delayed expert answers to the original visit without switching the active customer.
- Save voice visit notes; supply one approved short training video and question.
- Practise with a new associate. Measure whether they ask home questions, explain features, show a difference and complete follow-through with less assistance.

Completion: the associate can follow short instructions on a phone with one hand; the manager can inspect the saved evidence.

### P1 prepare the entry

- Test WhatsApp number, code link, demo video no longer than five minutes and one-page design note.
- Rehearse the ten-minute live demo separately from the submission video.
- Use only test people and recipients. Keep the code, documents and recordings within the required internal circulation.

## Verification required before claiming completion

| Check | Evidence to retain |
| --- | --- |
| FDK catalogue | Redacted successful JSON with IDs, TV filters, currency, price blocks, pagination and observed optional attributes |
| FDK promotions | Redacted result for confirmed slug/store/cart context; rule interpretation, expiry and unknown eligibility behavior |
| Data refresh failures | 403 HTML, malformed JSON, timeout, partial paging and stale snapshot cases; no fabricated or silently substituted facts |
| Sparse product facts | Missing brightness/Hz/HDMI, price range, missing store stock, variant ambiguity and duplicate names; safe display/ranking behavior |
| Commercial gates | Pre-demo bootstrap/chat/catalogue contain no prohibited promotional offers; after-demo eligibility is contextual and totals do not double-discount |
| Quote changes | Changed price/terms invalidates previews; frozen test purchase remains intact; unknown charge blocks final total |
| Channel replay | Duplicate webhook/button/retry produces one saved message/action; signature failure rejected; correct associate ownership retained |
| Media | Actual voice and label image, unclear model, transcription correction, unsupported fact and media failure |
| Latency and floor fit | Timestamped first reply under five seconds, three-line/three-button rendering on a real phone, long details accessible |
| Consent and delivery | Declined consent sends nothing; only allowlisted test recipients; transport failure is not marked delivered |
| Follow-through | Installation delay creates owned action; installation completion leaves working check pending; evidence is required to close it |
| Conversation quality | Seven steps scored 0–2 each, maximum 14, with supporting visit evidence and one improvement |

Extend the existing local journey tests around these integration risks. Add FDK contract fixtures from sanitized approved responses and fault cases. The existing Postman simulation covers OpenAI transport only; add an FDK dependency simulation when implementing and exercising the client, then separately verify authorized UAT reads. Mock success is not live access evidence.

The local `.postman/resources.yaml` has an empty workspace ID. A shared Postman owner contract is therefore not established by this checkout. Reuse the existing local artifacts now; bind/publish only when an owning workspace is actually required and available.

## Decisions needed from the supplied data owner

1. Which client/network context explains Postman's reported 200 versus this runtime's 403, and does the successful response contain the documented JSON `items` payload?
2. Which store ID, TV category/filter, cart type and representative product slugs should the demo use?
3. Where are approved physical stock, full TV specs, charges, finance terms and installation test data supplied?
4. What are the nested promotion rule meanings, stacking rules and authoritative price/application checks?
5. Which WhatsApp test number, test recipients, media and training video are approved?

The winning demonstration should make the observed store gaps visible: home questions before a shortlist, explanations tied to the room, a physical difference shown, every charge disclosed and a named owner checking that the TV works. The visit findings are directional evidence from nine scored conversations in one city, not a claim of proven impact from this software. Use the later live test to measure the improvement.
