# Web application contract

Reviewed voice-file input is documented in [the voice API contract](voice-input.md).
These authenticated upload/prepare/confirm/discard routes are active; the earlier
no-audio description below applies to the original release and legacy channel routes.

The authenticated development-only `/api/messaging/mock` routes are documented
in [the mock WhatsApp contract](mock-whatsapp.md). They reuse the saved customer
journey and do not send external messages. Text requests may optionally supply
`expected_version` to reject a stale visit before processing a new message.

The website replaces channel-specific entry points. FastAPI/Pydantic is the executable
contract; `postman/specs/store-iq.openapi.json` is generated from it. No WhatsApp,
audio, payment processing, or real customer delivery is enabled.

All private routes use an opaque, expiring HttpOnly session cookie. Associates can
access only their customers; admins can review all records. Login requires a saved
account and password; role is never accepted from the browser. Same-origin writes
are enforced. Development uses explicitly labelled synthetic accounts and data.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | /api/auth/login | Validate phone/password; set cookie |
| GET/POST | /api/auth/me, /api/auth/logout | Identity / revoke session |
| GET | /api/bootstrap | Permitted customers, stock, offers, tasks, training and notifications |
| POST | /api/customers | Allocate permanent per-associate serial; preserve duplicate names |
| GET | /api/customers/{id} | Full saved conversation and workflow |
| POST | /api/customers/{id}/messages | Contextual text coaching with retrieval citations |
| POST | /api/customers/{id}/actions | Explicit validated workflow transition, version checked |
| POST | /api/comparison | Compare 2–3 products; grounded AI verdict; no workflow transition |
| GET | /api/customers/{id}/summary | Deterministic current quote/handover |
| GET | /api/customers/{id}/summary.pdf | Generate and download current versioned PDF |
| POST/DELETE | /api/customers/{id}/share | Consent-gated immutable snapshot / revoke links |
| GET | /api/shared/{token} | Expiring customer-safe snapshot; no internal chat |
| POST | /api/requests | Deduplicate open expert escalation |
| POST | /api/requests/{id}/reply | Admin attributed reply with notification |
| POST | /api/requests/{id}/action | Assign, resolve, reopen or append follow-up |
| POST | /api/tasks/{id} | Update one owned task; working check gates closure |
| POST | /api/training | Persist answer and server-calculated feedback |
| PUT | /api/admin/products/{id} | Validated mock product update; stable changes dirty index |
| PUT | /api/admin/offers/{id} | Edit dated synthetic offer without reindexing |
| PUT | /api/admin/knowledge/{id} | Edit approved stable facts; mark index dirty |
| PUT | /api/admin/commercial/{id} | Edit charges and finance without reindexing |
| POST | /api/admin/reindex | Build embeddings + BM25 candidate index; atomic publish |
| GET | /health/live, /health/ready | Process / durable database health |

422 = invalid input; 401 = no session; 403 = role/origin/ownership violation;
404 = absent object; 409 = stale version or unmet journey precondition;
429 = rate limit; 502/503 = AI/configuration unavailable. AI failure never
substitutes a fabricated answer. User messages remain saved for retry.

Prices, stock, dates, offers, charges and finance are read at request time.
Stable facts alone are indexed. Offer eligibility is computed on the server
after confirmed home assessment and an actual demo with preference evidence.
No AI output can mutate customer stages, offers, tasks, sales or consent.
Share links expire after 7 days and may be revoked. Opening any screen is read-only.

## Guided associate conversation

Customer responses include `flow`: a server-derived prompt, up to three typed
buttons, the current home question, and safe commercial preview data. Buttons
either submit a validated action, open an inline input, or navigate to a detailed
screen. The browser does not decide offer or sale eligibility. Saved assistant
prompts carry button metadata so the guided journey is visible in history.

Additional customer actions: `ask_home`, `home_answer` (field/value), `continue_flow`,
`offers`, `ask_expert`, `expert_resolved`, `explain_another`. Normal text commands
(Correct, Demo A/B, Continue, Finance, Hindi, Summary, etc.) use the same handler;
sale, task completion and consent still require their explicit validated evidence.
Home answers advance one missing question at a time; question/expert interruptions
preserve the customer's journey. Resuming a saved visit never records a demo or sale.

## Reviewed journey changes (1 November 2026)

- `site` now requires separate nonempty `power`, `cable_route`, `access`, and
  `devices` answers alongside `placement`, `specialist`, and `notes`.
  `specialist` accepts `yes`, `no`, or `unknown`. Unknown material answers keep
  the total unconfirmed. Legacy note-only site records need a refreshed check.
  Home/shortlist/preferred-TV changes invalidate installation evidence; changes
  to costs clear payment preference. The saved site placement updates the home card.
- A one-TV shortlist supports `start_demo` and evidenced `demo`; it is recorded
  as a single-TV demonstration. The comparison endpoint still requires 2–3 TVs.
  `start_demo` optionally accepts `focus` for a requested repeat demonstration.
- Quotes expose `site`, `contact_owner`, `required_total`, `optional_total`, and
  a dependency `fingerprint`. Optional lines identify themselves and include
  approved descriptions or an explicit unconfirmed-terms fallback. Commercial
  records accept `soundbar_description` and `protection_description`.
- POST `/customers/{id}/share-preview` accepts the usual action envelope with
  `data.recipient` (a test recipient), current version and recorded consent. It
  generates the PDF and saves its hash, version, quote fingerprint and recipient
  for ten minutes. POST `/share` additionally requires `data.preview_id` and
  `data.confirmed=true`. Confirmation consumes that preview once; changed
  commercial data or customer versions require a fresh preview. Sharing records
  recipient/time/PDF version and creates an internal simulated link, with no
  external message delivery. Cancel creates no share.
- Pre-sale shared snapshots become outdated on dependent commercial changes or
  date-dependent offer changes. Completed purchase amounts remain frozen.
- Resolving an expert thread does not clear its critical decision hold. The
  request `resolve` action can additionally accept `data.evidence`: the verified
  answer/alternative and source (minimum ten characters), attributed and saved
  separately. Reopening a resolved identical question reuses its ID/history,
  clears decision evidence and starts a new timer cycle.
- Reopening delivery or installation invalidates dependent task completion and
  reopens a closed visit. Due tasks generate one internal notification per due
  cycle; rescheduling or reopening starts a new cycle. Consent remains explicit.
- Bootstrap customer, task and request scopes agree with associate/activity-date
  filters. Training attempts use associate/attempt-date filters in IST. The
  `scopes` field labels the independently scoped personal inbox and practice session.
- Bootstrap `practice` persists answered questions, current feedback, finished
  state and repeat cycle. POST `/training/session` accepts action `next`,
  `finish` or `repeat` with the standard action envelope.
- `correction` accepts `data.reason` after purchase (minimum ten characters),
  creating an internal store-manager review task. It does not amend purchased
  items, stock or frozen charges. Handover now says Review details explicitly.
- Written Hindi/Marathi guided prompts, buttons and principal form/action error
  prompts are deterministic and separate from deferred voice translation. Saved
  model names, catalogue terms and amounts remain unchanged. English remains
  available; this is not a claim that every website label is translated.
- Known model price questions, unambiguous customer date searches and supported
  preference changes are handled before AI routing. Brand/size constraints are
  saved independently of explicit product IDs; changed choices clear stale
  demo/site/payment evidence. Date searches preserve the active visit and link
  to filtered customers; ambiguous or reversed ranges ask for correction.

The frontend acknowledges AI work immediately with an accessible live status.
The message API returns a completed customer with 200 when ready within 1.5 seconds,
or a durable processing receipt with 202. Clients must poll the receipt's authenticated
`status_url` until 200, or surface its retryable error. A 202 receipt acknowledges
saved input; it does not claim a final answer or completed business action.
Scores expose 0/1/2 evidence and `applicable`; unfinished reviews use the applicable
denominator. The final closed-visit denominator remains 14.

## Text acceptance changes on 6 November 2026

`POST /api/customers/{id}/messages` accepts the same text envelope. `request_id`
is 1-100 ASCII letters, digits or `_.:-`; reuse is permitted only for identical
text. A conflicting reuse returns 409. Exact retries never repeat a sale or task.
Only slow AI requests consume the AI rate limit; deterministic workflow replies
do not consume the model-call budget. Another in-flight message for the same
visit is rejected until its result or retry is available.

Example processing receipt (202, `Retry-After: 1`):

```json
{
  "status": "processing",
  "request_id": "visit-question-1",
  "acknowledgement": "Checking the latest details. Your message is saved.",
  "status_url": "/api/customers/CUSTOMER_ID/message-results/visit-question-1"
}
```

`GET /api/customers/{id}/message-results/{request_id}` checks ownership and returns
202 while processing, the current result customer on completion, or a retryable
error. Retry by posting the original text and request ID again. Receipts survive
restart; interrupted work becomes retryable rather than falsely completed. The
supported deployment remains one application replica. Stale AI completions cannot
overwrite a visit changed by another action.

The backend now collects these inputs through saved text state as well as forms:

| Text | Next interaction |
|---|---|
| Site check | Wall/table, power, cable route, access/space, devices and specialist work, one missing answer at a time; explicit comma-separated checks can be supplied together |
| Optional extras | Add/Remove soundbar or protection; Done shows itemised cost |
| Full cost / Summary | Itemised required charges, optional amount, unknown details, finance and PDF URL in messages of up to three lines |
| Confirm sale | Shows the current amount; requires `Confirm AMOUNT`, bound to the quote fingerprint; Cancel has no sale effect |
| Save follow-up / Save for later | Reason, explicit Yes/No contact permission, future time with timezone or store-local IST, then owner |
| Completed / Problem | Selects next handover task; collects evidence, owner and next-update time; explicit `installation problem` can reopen installation |
| Share summary | Requires consent; collects test recipient and generates a versioned PDF preview |
| Confirm share / Cancel | Consumes the current preview once, or cancels; sharing remains simulated |
| Revoke share | Revokes the customer's earlier summary links |
| Customer list / All customers | Date choice or paged serial list; Today, Yesterday, Date range, Next, Previous and numeric serial selection |
| New customer NAME | Creates a separate numbered record and returns that customer as the message result |
| Edit / Edit details | Asks which home field and its corrected value; reconfirmation is required |
| Demo done | Model/letter followed by reason, or model and `because` reason together |
| Need another demo / Demo unavailable | Collects the focus or reason; does not fabricate demonstration evidence |
| Visit note TEXT | Saves an attributed visit note |
| See score | Displays seven evidence-based step scores |
| Customer understood TEXT | Records the customer's response to the latest supported Validate/Translate coaching; enables full evidence credit |

Input collection supports Cancel and expert/language interruptions. Existing
structured action validation, unknown-charge holds, expert blockers and working-check
gates are shared with the forms. Typing a serial switches customers only inside
customer-list selection. The returned customer ID can therefore differ from the
requested ID; clients must display the returned customer. The website does this.

Shift text accepts `start`, `Start shift`, `TV`, `skip_practice` and `Skip practice
today`. Start asks the department; TV returns a current-data brief. Missing video
and daily change-log facts are labelled unavailable rather than invented.

Scoring gives partial credit for a sourced coaching answer and full credit only
with recorded customer-response evidence. An internal 14/14 is not a judge score.
New photo input is intentionally outside this change's scope.
