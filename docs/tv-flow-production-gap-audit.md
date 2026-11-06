# Store IQ TV flows: production API gaps and required fixes

Reviewed 4 November 2026. Internal confidential use only.

## Outcome and scope

The website already implements much of the saved customer journey. The main blockers are disconnected WhatsApp/voice/photo support, synthetic commercial facts, and a product model that cannot safely accept the real catalogue. Connecting a product endpoint alone will not complete the contest journey.

Use **`https://www.reliancedigital.in`** for the integration described here. The verified product route is **`/ext/raven-api/catalog/v1.0/products`**. Do not continue the earlier UAT authentication permutations. Replacing `/service/application` with `/ext/raven-api` works for the observed catalogue request, but **has not produced a working promotion API**.

This document is the new implementation backlog requested against [the TV flows](tv-store-associate-flows.md). It changes no application behavior. It supplements [the earlier FDK plan](fdk-uat-update-plan.md): retain that document's historical evidence, but use the fresh production findings below for endpoint and parser decisions.

Evidence labels:

- **Code:** established by inspection of the current repository; not a claim about deployed records.
- **Live:** read-only production GET performed in this review.
- **Required:** proposed implementation or acceptance check; not already completed.
- **Unknown:** no successful contract/response establishing the capability.

## 1. What is actually running

| Code | Current behavior | Implication |
| --- | --- | --- |
| `app/main.py` | Mounts `app.web.api`, serves React, initializes SQLite and starts reminders | Extend this application and its saved journey |
| `app/web/store.py`, `seed.py` | Persist customers, messages, tasks and training; seed eight synthetic TVs, offers, people and knowledge | Durable storage is real; seeded facts are fixtures |
| `app/web/api.py`, `domain.py`, `actions.py`, `flow.py` | Authenticate, enforce ownership/version checks, collect home details, gate actions, calculate quotes and record explicit test sales | Reuse these rules for both channels |
| `app/web/intelligence.py` | Uses the OpenAI SDK, structured outputs, BM25 and vector retrieval when configured | Active AI is not the legacy fixed mock; its product facts remain synthetic |
| `frontend/src` | Website chat, catalogue, comparison, summary/PDF, training and manager operations | These screens do not prove WhatsApp completion |
| `app/legacy.py`, `app/meta`, `app/recordings`, `app/catalog` | Separate retained adapter/regression scaffold | Not mounted into the active web journey |

Specific seams that must be removed or kept explicitly test-only:

- `app/catalog/provider.py`: `get_catalog()` always returns `EmptyCatalogProvider`, with unavailable status and empty product/offer/stock/finance lists. It is not the active website's data source.
- `app/meta/client.py`: mock mode fabricates a message ID without HTTP. Its live branch sends text to allowlisted test recipients; it does not implement the complete interactive/media workflow.
- `app/meta/router.py`: validates/deduplicates incoming events in PostgreSQL, but only inserts an inbox record. It does not run the SQLite website journey, and `app.main` does not mount it.
- `app/recordings/transcription.py`: `PendingTranscriber` raises an integration-not-configured error; `mock_recording_text` substitutes typed text for audio.
- `app/web/seed.py`: invented model names/specs, local quantities, future arrival dates, dated fixed discounts and six training questions. Example: Vision Q55 and its 600-nit specification are fixtures, not production Samsung facts.
- `app/web/store.py`: default commercial terms are delivery INR 0, installation INR 499, mount INR 1,499, soundbar INR 7,999, protection INR 3,999, 12-month finance, INR 999 fee and zero APR. None is established by the supplied two FDK methods.
- `app/web/api.py`: `Product` requires populated specs and integer stock; admin product saves force `mock=True`. `Commercial.finance_apr` only accepts zero. Imported facts cannot simply be passed through these schemas.
- `app/web/intelligence.py`: product chunk titles say “synthetic specifications”; the system prompt says synthetic data and typed text only, explicitly excluding photo, scan, voice and WhatsApp requests.
- `frontend/src/ui.tsx`: TV artwork is generated from scene/CSS elements, not catalogue product imagery. Catalogue brand/size options are hardcoded in `catalogue.tsx`.
- `postman/mocks/openai/default.js` and the legacy mock AI are useful test seams, not evidence of real speech, photo recognition or model quality.

## 2. FDK reference versus production responses

The DOCX defines only two methods: `getProducts` and `getPromotionOffers`. It does not define store inventory, product-detail lookup, financing, orders, payment, delivery or installation-job APIs. Those capabilities need approved data or additional contracts; do not invent endpoint paths for them.

### 2.1 Request/response evidence

Production observations began at **2026-11-04T17:21:26Z**. Counts, prices and ordering are observations at that time, not permanent constants. No production writes, checkout, payment, inventory reservation or customer messages were performed.

| Check | Request against `https://www.reliancedigital.in` | Observed result | Meaning |
| --- | --- | --- | --- |
| Supplied catalogue shape | `GET /ext/raven-api/catalog/v1.0/products?page_id=%2A&page_size=12&q=tv` | 200 JSON; 12 items; keys `items`, `filters`, `page`, `sort_on`, `smartFilters`, `meta` | Working catalogue read |
| Minimal-header catalogue check | Same URL, Postman CLI with Accept and supplied Bearer credential | 200 JSON; three assertions passed; exit 0 | Browser, cookie, copied date and signature headers were unnecessary for this request at this time |
| Cursor follow-up | Same catalogue, `q=tv&page_size=12&page_id=1` | 200 JSON; same 12 IDs, `current=0`, `next_id="1"` | Blindly following `next_id` as `page_id` would loop |
| Explicit number page 1 | `q=tv&page_size=12&page_no=1&page_type=number` | 200 JSON; same first 12 IDs; `current=1`, `next_id="2"` | Explicit first page works |
| Explicit number page 2 | `q=tv&page_size=12&page_no=2&page_type=number` | 200 JSON; 12 IDs with no overlap with page 1; `current=2`, `next_id="3"` | Number paging advanced in the sampled pages |
| TV category restriction | `q=tv&page_size=12&page_id=%2A&f=category%3Aled-televisions` | 200 JSON; `item_total=336`; all 12 sampled items categorized LED Televisions | This observed filter excludes the sampled media-player result; not a complete import |
| Promotion route substitution, product context | `GET /ext/raven-api/cart/v1.0/available-promotions?slug=<returned-product-slug>&page_size=12` with replay headers | 200 `text/html;charset=UTF-8`, starting `<!doctype html>` | Storefront HTML, not `PromotionOffersResponse` |
| Promotion route substitution, no query | `GET /ext/raven-api/cart/v1.0/available-promotions` with replay headers | 200 HTML | Not an empty offer list or usable API success |
| Promotion route, minimal Postman request | Same no-query route, Accept/Bearer | 406 with empty body; three contract assertions failed; CLI exit 3 | Header/client-dependent failure; still no verified promotion response |
| Documented service route on production | `GET /service/application/cart/v1.0/available-promotions?slug=<returned-product-slug>&page_size=12` | 200 `text/html` | Moving the old route to the production host also did not establish promotion access |

The replay used the supplied Bearer, SDK version/date/signature, browser user agent, INR and country headers. The minimal catalogue request used only explicit Accept/Bearer headers, in addition to client defaults. These are separate observations, not proof that headers are interchangeable for every route. Authentication renewal, expiry and signing requirements remain unknown. Do not commit the supplied token, copied signature, cookies or other secret values.

The production storefront JavaScript inspected during this review still contained the SDK mapping `getPromotionOffers -> /service/application/cart/v1.0/available-promotions`. That string establishes a client mapping, not a functioning request with the right runtime context. The correct reachable production promotion route/authentication/context remains an integration dependency.

### 2.2 Actual product payload and important mismatches

The first item was Acer AR32HDGGR2841AD, `uid=8880020`, `item_code="494496158"`. Its observed price blocks were:

```json
{
  "effective": {"min": 8999, "max": 8999, "currency_code": "INR"},
  "marked": {"min": 24999, "max": 24999, "currency_code": "INR"}
}
```

The item had `sellable=true`, `sizes=["OS"]`, `variants=[]` and image objects under `medias`. There was no populated `highlights` or `short_description` value and no `selling` price block. Do not require every optional field described in the DOCX to exist.

| Observed field | Correct interpretation / required mapping | Current incompatibility |
| --- | --- | --- |
| `uid`, `slug`, `item_code`, identifiers/EAN | Preserve external IDs and SKU/EAN lookup; use stable namespaced local identity | Current IDs are synthetic strings; no external identity/provenance model |
| `brand.name`, `name`, `attributes.model` / `model-name` / manufacturer part number | Preserve display name and model aliases for text/photo matching | Existing model names are fixture labels |
| `price.effective`, `price.marked` | Retain ranges, currency, source and fetched time; quote a single amount only for confirmed price/variant context | Current `price` is one required integer and assumes INR |
| `attributes.screen_size_diagonal="80.01 cm - 32 inch"` | Normalize explicit inches with unit validation | `sizes=["OS"]` is not screen diagonal; current filters only list 43/55/65 |
| `attributes.screen_resolution="1366 x 768 -HD"` | Preserve verified resolution; support HD/FHD as well as 4K | Seed assigns every TV 3840 x 2160 |
| `attributes.panel_type="VA"`, `display_type="HD Ready"` | Separate panel technology, backlight/display family and resolution class | Existing enum LED/QLED/OLED/Mini LED cannot represent these different dimensions |
| `attributes.no-of-hdmi-ports="3"`, `rated_speaker_output_power_rms="24 watts"`, `warranty="2 Years"` | Parse supported keys/units; retain original values and source | Required integers/defaults would force guesses if absent |
| `attributes.tv_operating_system` on some other items | Optional OS mapping; approved text extraction can supplement with traceable evidence | No uniform OS key across the sample |
| `attributes.key-features`, description/SEO HTML | Sanitize to text; extract only supported facts and retain source | Never render raw HTML or treat retrieved text as instructions |
| Missing brightness/native refresh/viewing-angle fields | Unknown unless supported by another approved field/document; descriptive refresh claims need semantic review | Ranking and reasons currently assume numeric brightness/Hz and a known angle |
| `sellable`, quantity-like attributes, empty `store_ids` / `store_id_list` on first item | Online listing availability only; no established physical-store on-hand quantity | Ranking filters on `stock > 0`; test sale decrements it |
| `medias[].url`, `.type`, `.alt` | Approved real image display with fallback and suitable CSP/cache policy | Existing CSS scenes are not product photography |

Real data also conflicts: item `uid=9546382` had `display_type="Full HD"` alongside `screen_resolution="3840 x 2160 - Ultra HD"`. Flag conflicting fields and hold the affected claim for review. Do not silently choose the higher specification or let the LLM resolve the conflict as fact.

### 2.3 Search and paging corrections

The unfiltered `q=tv` response reported `item_total=371`, while only 12 items were returned. It included an Amazon item under **Smart TV Converters & Media Players**. Filters also offered soundbars, mounts and other categories. `smart_filters_categories` misleadingly contained `smart-phones`; it is not authoritative TV classification.

Required behavior:

1. Use response-discovered categories and validate each imported item's category. Keep accessories in a separate set. `category:led-televisions` is a verified sampled filter, not proof that every TV technology has been enumerated.
2. Start verified number pagination explicitly at `page_no=1&page_type=number`; request successive pages with the same query/filter/sort. Validate returned page progression and product IDs.
3. Stop on `has_next=false`; detect repeated IDs/page tokens, cap requests and preserve a partial-sync error. Never report a full catalogue after one page or a loop.
4. Do not interpret `item_total` as the current page length. The observed response had no separate `item_count`, `size` or `limit` field.
5. Generate brand, size and feature choices from approved normalized data. Use returned sort values: `popular`, `latest`, `price_asc`, `price_dsc`, `discount_dsc`, `discount_asc`, `rating_dsc`, `relevance`.

Only the sampled pages and one category filter were checked here; full traversal, combined category/brand/range filters and catalogue completeness remain unverified.

### 2.4 Promotions: blocker and safe fallback

The DOCX expects `available_promotions[]` with IDs, buy rules, discount rules, promotion type/group, text, description, gifts and `valid_till`. None of those response fields was verified from a live promotion response in this audit.

- Validate HTTP status, JSON content type, parseability and expected schema. HTML 200 and empty 406 must become an unavailable integration state, never “no eligible offers” or a confirmed discount.
- Obtain a working production request with a real returned slug and, when required by the confirmed contract, correct store/cart/promotion-group context. Do not use the DOCX's illustrative `store_id=1` or `promotion_group="value"` as real context.
- Preserve nested rules, gift items and timestamp/timezone. An offer being listed does not establish eligibility, stacking or application to a final cart.
- Replace the current brand/minimum-size/fixed-discount model before importing provider promotions. `max(discount)` in `domain.quote()` is safe only within the current fixture assumptions.
- Never subtract the marked/effective price difference a second time. Product `discount`, teaser/countdown tags and `_custom_meta` bank/coupon/promo strings are not proof of an applicable additional discount.
- Until access is established, show “Offer not confirmed” and route to an expert/admin. Approved test offers may be used in a clearly identified fixture mode; never quietly combine them with production catalogue prices.

## 3. Required fixes for every requested flow

Priority: **P0** blocks a credible contest journey or factual correctness; **P1** completes the requested experience; **P2** adds resilience/polish after that journey works. “Existing” means code-inspected foundation, not fresh end-to-end validation.

| Flow in `tv-store-associate-flows.md` | Existing foundation | Fix and dependency | Acceptance evidence required |
| --- | --- | --- | --- |
| Shared WhatsApp/website identity and login | Password-authenticated test phone accounts, saved roles, ownership checks | **P0:** bind verified test WhatsApp sender to the same associate/customer records. Extract a shared application service rather than run a second PostgreSQL journey. **P1:** authenticated deep links to customer/screen; OTP before real use | Start on approved test WhatsApp, continue on website, return to same customer; another associate cannot access it; typing an admin number never grants a role |
| Customer lists, names, serials and dates | Permanent per-associate serials, duplicate-name handling, IST activity filters and website chat-list pagination | **P0:** implement channel-neutral selection/list state. **P1:** voice-name ambiguity asks resume/new; preserve filter/cursor; serial selection only while choosing a customer | Duplicate names remain separate; 3 entries/message; Today/Yesterday/inclusive range, empty results, previous/next and admin-associate filter work identically across channels |
| 1. Before shift and practice | Shift record, catalogue, offer schedule and saved six-question practice | **P0:** WhatsApp start/TV/brief actions; source-aware stock/offer brief. **P1:** compare snapshots for actual changes, approved short video when available; preserve separate website training | Brief says unavailable when no confirmed stock/change feed; video missing is disclosed; next/finish/repeat saves attempts without treating an unanswered question as wrong |
| 2. Start customer | New customer and saved text messages | **P0:** download actual test voice media, transcribe and feed the shared customer creation flow; confirm uncertain name/home extraction | A real test audio note creates/resumes the intended record; new customer saves the prior visit; retry does not duplicate customer/message |
| 3. Understand home | Seven home fields, one missing question, Unknown handling and explicit confirmation | **P0:** voice/photo transport must preserve corrections and Unknown; keep confirmation gate; support audio transcript review | Known fields are not re-asked; one missing question at a time; edit invalidates affected recommendation/demo/quote state; no appearance-based budget inference |
| 4. Handle belief/doubt | Grounded typed coaching, source references and return-to-flow buttons | **P0:** source real/approved facts and channel rendering; strengthen validation quality with the “all 4K TVs are the same” case | Confirm the correct resolution point, politely explain supported differences, tie to daylight/home and return to the saved step; no unsupported brand claim |
| 5. Explain label | Typed model/feature explanation only | **P0:** image upload/download, OCR/vision, SKU/EAN/model matching, ambiguity and wrong-model reset. Update the text-only AI prompt only after media exists | Actual label photo maps to an approved product; unclear/unknown label asks for a closer photo or typed model; explanation uses verified feature and home context |
| 6. Recommend up to 3 | Budget cap, preference filters, deterministic ranking, saved selections | **P0:** production normalization plus approved store availability; null/conflict-aware scoring. **P1:** all A/B/C options need a home reason and meaningful trade-off | Accessories never appear as TVs; one/two matches stay one/two; no fabricated stock/specs; lower range/other brand/smaller size updates saved preferences |
| 7. Show difference | Demo plan and explicit preferred-model/reason evidence; unavailable path | **P0:** WhatsApp demo instructions and buttons using same state. Preserve actual-demo gate | Same clip/matched settings and home-specific check; opening comparison or sending instructions never completes demo; unavailable demo remains incomplete |
| 8. Full solution/cost | Itemised quote, site form, extras selection and specialist-charge blocking | **P0:** approved charge feed/test pack with nullable values and provenance; accessory compatibility and coverage facts. **P1:** collect site details one at a time in chat | Unknown delivery/installation/mount/site work remains pending; subtotal is not a final total; optional items added only by choice; full charges visible in chat/website/PDF |
| 9. Offers/payment | Home/demo/cost gates, payment preference, explicit test sale | **P0:** resolve promotion API or explicit approved fixture mode; represent supported rules. Replace zero-only finance assumptions with approved plan terms and eligibility | Early price question gets known price; offers remain gated; full finance sentence includes upfront, count, EMI, fees, total, APR/interest and missing terms; preference takes no payment |
| 10. Decide later/unavailable | Consent, due time, reason and owned follow-up task | **P0:** separate physical-stock unknown from zero; remove generated arrival promises. **P1:** channel reminders and revalidation | Unknown availability is not “out of stock”; no invented arrival date; returning visit refreshes price/offer; declined contact remains internal |
| 11. Delivery/installation handover | Explicit synthetic sale, frozen quote, separate delivery/installation/working-check tasks and consent | **P0:** accurately label internal test tasks versus external confirmed jobs; carry site needs and owner. External jobs need another contract | Requested slot remains pending; no claim that resQ/order/payment exists; no-consent summary stays internal; sale not triggered by page navigation |
| 12. Follow through until working | Persisted reminders, problem/reopen paths, ordered completion checks | **P0:** WhatsApp associate notifications; retain next update time/owner. **P1:** map external statuses only after a job contract exists | Delayed/unanswered/cancelled job stays open; installation alone cannot close visit; working check records picture, sound, devices and satisfaction |
| 13. Review/coaching | Seven-step 0–2 evidence scoring and next-time prompt | **P1:** present stable score out of 14 plus pending/not-applicable explanation; avoid partial denominators implying final completion. Add real voice visit notes | Website and WhatsApp agree on evidence; one actionable improvement; practice excluded; good source references alone do not replace quality review of the explanation |
| Comparison | Two/three-product API, AI verdict, website specs and demo navigation | **P0:** nullable production specs and source-aware prices/availability; concise WhatsApp comparison. **P1:** sensible single-option path when only one TV fits | Relevant differences, home reason, trade-off and missing facts visible; selecting preferred TV is not a sale or completed demo |
| Ask expert/admin | Hybrid retrieval, persisted requests, attributed replies, blocking decisions and notifications | **P0:** same request/thread on both channels; attach approved media/source context; delivery outbox/status/retry | Admin answer reaches original customer thread and associate on website + test WhatsApp, without switching their active customer; failed delivery never marked delivered |
| Expert wait/escalation | `reminder_cycle()` currently uses hardcoded 120/300-second thresholds, persisted flags and admin notifications | **P1:** configurable thresholds, available-admin/manager routing and explicit waiting-for-assignment fallback | Assignment does not reset clock; one reminder/escalation per cycle; answer stops timers; reopen starts cycle; follow-up task does not resolve unanswered request |
| Summary/PDF/share | Real PDF, preview/consent flow, versioned expiring/revocable snapshot link; website explicitly simulates share | **P0:** same normalized facts/unknown amounts in PDF. **P1:** preserve simulated contest share and record recipient/time/version; distinguish link creation from transport delivery | Preview and confirm required; changed summary invalidates share/PDF; no real customer recipient; quote versus test purchase labelled correctly |
| Manager and languages | Admin filters, attributed actions and English/Hindi/Marathi support | **P1:** test real audio/text in Hindi and Marathi, verify output and fonts, manager filters and notifications. Keep model names/amounts unchanged | Same scenario understandable in all three languages; PDF legibility checked; manager can filter own permitted scope by associate/date and see request status |

### Concrete code defects to address during integration

1. **Required-field assumptions:** `Product`, ranking, reasons, comparison, RAG chunk construction and summary access mandatory scalar fields. Make unknown/conflict handling consistent throughout, not just in an importer.
2. **Recommendation reasons:** `domain.recommendation_reason()` uses price delta and Hz/size against A for B/C; it does not guarantee a customer-specific reason and main trade-off for each. Tie all options to this home and supported evidence.
3. **Offer exposure:** `GET /api/bootstrap` returns all offer records even before a selected customer's assessment/demo gate. Separate permitted shift-change summaries from actionable promotion details; do not rely solely on hidden UI elements to enforce the customer offer gate.
4. **Stock semantics:** `recommendations()` requires `stock > 0`, and `sale` decrements local stock. Never convert storefront `sellable` or quantity-like attributes to physical store stock. Keep synthetic allocation separate from imported facts.
5. **Review denominator:** `flow.build()` uses `2 * applicable steps` while the requested contest score is out of 14. Show earned/14 with pending explanations, retaining truthful partial evidence.
6. **Media and image policies:** `app/main.py` disables microphone/camera permissions, restricts images/connects to self and limits writes to 100 KB. Website audio/photo and real CDN imagery need deliberate upload limits, media handling and narrowly scoped policy updates.
7. **Latency:** the active SDK timeout is 30 seconds and a message may perform several model calls before returning. Existing validation records an 11.2-second comparison sample. No measured sub-five-second first reply exists here. Send a useful acknowledgement before five seconds, process slow work asynchronously and deliver the final result to the original customer context.
8. **Expert timers:** thresholds are hardcoded and escalation notifies admins rather than proving assignment to another available owner. Implement the requested routing/configuration while preserving persisted once-per-cycle flags.

## 4. Implementation work packages

### P0-A: Normalize catalogue facts before connecting the UI

- Add a production Raven read adapter consumed by the active SQLite application service, not only the unused `EmptyCatalogProvider`.
- Configure base URL and credential server-side. Do not forward the Bearer to React, logs, PDFs or RAG. Capture transport/schema failures separately from empty result sets.
- Retain raw provider data and a normalized record with external IDs, source/environment, retrieval time, source version/hash and per-field provenance. Store approved manual enrichments separately from imported facts.
- Support nullable specs, monetary ranges/currency and availability states such as unknown/online-sellable/store-confirmed. Keep raw strings for audit and normalize only well-understood units.
- Import explicit category-approved TVs with verified number paging and duplicate/loop checks. Stage and validate a snapshot before publishing; retain the last good snapshot with a visible stale status on failure.
- Separate fixture/imported modes. `DEMO_MODE=false` currently does not by itself replace catalogue/commercial seeding. Prevent real products from silently inheriting fixture stock, offers, finance or charges.
- Update Product/admin schemas, recommendations, reasons, catalogue/detail/comparison, RAG, quote, summary/PDF and stale-quote checks together. Imported changes must invalidate affected quote/share versions and refresh factual indexes.
- Replace blanket synthetic labels only for imported/approved fields; preserve test customer/sale/fulfilment labels. Update architecture/contracts and `.env.example` after implementation.

### P0-B: Get authoritative commercial inputs

- Obtain the working production promotion request and representative success/empty/error/rule examples. Keep its route unresolved until a JSON contract passes; do not announce Raven cart integration from the current observations.
- Obtain approved test store inventory/display stock, delivery/installation/site/mount charges, optional item compatibility/coverage and finance terms. The supplied DOCX cannot supply these.
- Represent unavailable as unavailable, not zero, free delivery, no offers, zero APR or stock zero. Block only the affected finalization while allowing unrelated questions and demonstrations.
- Revalidate changing price/availability/offer facts before explicit test-sale confirmation. Preserve frozen sale quote, idempotency and recorded provenance; do not introduce production checkout/payment as part of this audit.

### P0-C: Connect one approved test WhatsApp number to the shared journey

- Extract reusable customer/action/message services from route handlers; carry authenticated associate, customer ID, version, request ID and channel metadata through both adapters.
- Wire webhook verification, durable inbox, worker, shared dispatch and outbound delivery into `app.main`; use one authoritative customer store. Record inbound message IDs and outbox IDs to prevent duplicate state changes/replies.
- Implement text, supported interactive replies, audio and image media handling; real transcription and label matching; failure/uncertainty prompts; test-recipient restriction.
- Support Start shift, new/resume/list/date selection, demo, costs, payment preference, expert requests and task updates on WhatsApp. Website links complement the short replies and preserve context.
- Acknowledge slow operations under five seconds. Each bot message has at most three lines and three buttons; keep longer content in requested follow-ups or authenticated website views.
- Deliver expert and task updates to the original associate/customer context; persist sent/delivered/failed state separately from website read state. Retain consent/preview/test-only sharing safeguards.

### P1-D: Finish requested details and prove the contest story

- Configurable escalation, multilingual audio/text, voice visit log, approved shift video, dynamic brand/size filters, complete A/B/C reasons, score/14 and summary/PDF consistency.
- Validate deep links, cross-channel history, duplicate names, ambiguous voice names and inclusive IST activity dates.
- Use the existing tests as regression coverage, then add meaningful boundary cases below. Existing local/AI simulation evidence must not be reported as live catalogue/WhatsApp proof.
- P2: improve operational visibility, refresh/backoff behavior and larger catalogue performance once the P0/P1 story is working.

## 5. Endpoint coverage and verification plan

### Existing application API surface to preserve

These paths are code-inspected, **not HTTP-tested in this audit**. They operate on local records, not directly on FDK responses.

| App endpoint | Response/behavior dependency after the fix |
| --- | --- |
| `POST /api/auth/login`, `GET /api/auth/me` | Safe test identity/role; shared WhatsApp mapping must not bypass ownership |
| `GET /api/bootstrap` | Filtered local customers/tasks/requests, product snapshot and metadata; source/freshness and gated offer projections needed |
| `POST /api/shift`, `POST /api/training`, `POST /api/training/session` | Persisted shift/practice state; approved current brief/video data supplied separately |
| `POST /api/customers`, `GET /api/customers/{id}` | Stable local customer identity/serial and saved flow across channels |
| `POST /api/customers/{id}/messages`, `/actions` | Shared deterministic state transitions; provider work does not bypass version/idempotency checks |
| `POST /api/comparison` | Current response has `products` and grounded `verdict`; tolerate missing/conflicting specs |
| `GET /api/customers/{id}/summary`, `/summary.pdf` | Same itemized quote/pending facts, source/version and quote/test-purchase status |
| `POST /api/customers/{id}/share-preview`, `/share`; `DELETE /api/customers/{id}/share`; `GET /api/shared/{token}` | Consent/preview/version/revocation retained; simulated share remains distinct from transport delivery |
| `POST /api/requests`, `/requests/{id}/reply`, `/requests/{id}/action` | One saved expert thread, statuses and attributed actions; add channel-delivery records |
| `POST /api/tasks/{id}`, `/api/notifications/{id}/read` | Separate owned work and read status; external status requires external evidence |
| `PUT /api/admin/products/{id}`, `/offers/{id}`, `/commercial/{id}`, `/knowledge/{id}`; `POST /api/admin/reindex` | Separate imported, approved manual and fixture data; null-aware schema and reindex/version invalidation |

### Checks actually run in this review

- Read the DOCX's complete paragraph/table text and both two-page PDFs; inspected the requested flows, active/legacy code, frontend, API schemas, existing plans and validation records.
- Ran only read-only production GET probes listed in section 2, plus production homepage/client-JavaScript inspection. Temporary raw captures were kept outside the repository; this file records sanitized observations without credentials.
- Postman catalogue: HTTP 200, JSON content type, and exactly 12 items each containing `uid`/`slug`: **3 passed, exit 0**. This establishes the sampled listing shape, not correct category, store stock, complete pagination or quote eligibility.
- Postman promotion minimal-header request: HTTP 200 assertion, JSON content-type assertion and `available_promotions` array assertion: **3 failed, exit 3**, on an observed empty 406. Replay-header probes separately returned HTML 200. Neither is a usable promotion response.
- No application tests, live speech/photo processing, WhatsApp delivery, finance approval, external job creation or complete catalogue sync were run. No application code/configuration changed.

### Required acceptance checks after implementation

| Boundary | Required proof |
| --- | --- |
| Transport/schema | Reject HTML 200, empty 406, bad JSON and wrong schemas; retain last good snapshot as stale; distinguish failure from valid empty results |
| Catalogue | Verify page 1/2 progression and full import termination; repeated page stops safely; accessory excluded; stable IDs and no duplicates |
| Normalization | Handle 32-inch HD and larger 4K TVs, absent selling/highlights/specs, price ranges, unit strings and conflicting display/resolution; no fabricated values |
| Recommendation | Unknown stock/specs do not become numeric facts; all options fit stated range and have supported home reason/trade-off; fewer than three is valid |
| Quote/promotion | Missing charges block final total; no double discount; supported offer eligibility and expiry/timezone; unknown finance terms remain pending |
| Workflow | Early offer, page-view demo/sale, stale write and duplicate webhook cannot bypass gates; payment choice never collects money |
| Channel/media | Actual allowlisted test audio/photo, transcript/model corrections and identical customer history; useful first reply under five seconds; maximum 3 lines/3 buttons |
| Expert/follow-up | Admin delay, assignment, reopen and delivery-failure scenarios; once-per-cycle reminders; no active-customer switch; unknown facts remain blocked |
| Handover | Consent/no-consent, requested slot, problem/reopen and separate working check; cancelled/unanswered installation remains unresolved |
| Summary | Preview, regenerated PDF after changes, recipient/version history, revoked link and no private coaching in customer view |
| Languages/manager | English/Hindi/Marathi scenario and PDF readability; activity-date and associate filters; no unauthorized role/data access |

For code paths calling upstream services, use the repository's Postman simulation workflow to exercise timeouts, rate limits, malformed payloads and outages without production writes. Keep fixture/simulation results separate from the later read-only live integration checks and actual approved test-channel evidence.

## 6. Contest focus and definition of done

The [contest brief](../6_Reliance_Digital_Store_IQ_Contest_28Oct2026.pdf) gives 25 demo points to end-to-end WhatsApp, 25 to required steps/reasons, 20 to floor fit, 20 to correctness/safety and 10 to extras. Demo and subsequent live test each carry 50% of judging. The submission deadline is 6 November at 18:00; the brief lists a test WhatsApp number, code link, at-most-five-minute video and one-page design note as deliverables. A polished website alone cannot establish the WhatsApp criterion.

The [store observations](<../Store_Visit_Findings_Reference_27Oct2026 (1).pdf>) make the priorities concrete: median score 6/14, price first in 6/6 Reliance conversations, median two home questions, weak explanation and an installation case never checked to completion. Preserve home-first discovery, truthful feature explanations, real demonstrations, complete charges and an owned working check as data/channels change.

Complete the [ten-minute TV story](tv-store-associate-flows.md#10-minute-tv-demo-story) with test people and approved test data:

1. Start shift on the test WhatsApp number; show sourced stock/offer status and practice/video availability.
2. Send actual audio with the living-room/cricket/movies/daylight/side-seating needs; ask only missing questions and confirm the home card.
3. Handle the 4K doubt, then send an actual label photo; show verified model evidence and uncertainty handling.
4. Recommend up to three appropriate TVs, explain every choice, compare and record an actual physical-demo preference/reason.
5. Itemize required/optional charges; show only confirmed applicable offer and full finance terms, or explicitly pending facts with an expert path.
6. Record payment preference and explicit test sale separately; capture consent, generate current PDF and simulate sharing to a test recipient.
7. Show separate delivery/installation/working-check tasks, an installation delay and an attributed expert reply on both channels.
8. Resume the same serial on website and WhatsApp; show score out of 14, next improvement and manager view.

**Done means observable completion of these steps with truthful sourced facts and working state transitions.** Catalogue access does not imply verified stock, promotion eligibility, finance or external fulfilment. Production reads are integration evidence; the contest still requires test data/test recipients and simulated customer delivery. Keep a clearly identified approved test snapshot/mode for the demonstration rather than silently claiming production commerce operations.

## Source index

- [TV associate flow specification](tv-store-associate-flows.md): all 13 flows, supporting channel rules, expert workflow, summary and demo story.
- [FDK v1.9.5 UAT method reference](../FDK_Method_Reference_v1.9.5_UAT.docx): `getProducts`, `getPromotionOffers`, request/response tables and UAT URLs.
- [Contest brief](../6_Reliance_Digital_Store_IQ_Contest_28Oct2026.pdf): pages 1–2, journey, floor/data rules, judging and submission.
- [Store visit findings](<../Store_Visit_Findings_Reference_27Oct2026 (1).pdf>): pages 1–2, observed discovery/explanation/follow-up problems and study limits.
- [Earlier FDK integration plan](fdk-uat-update-plan.md) and [existing validation](validation.md): historical evidence, not substituted for this review's live checks.
- Source code cited by repository path throughout; production response observations are recorded in section 2.
