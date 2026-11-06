# Store IQ web architecture

As of 5 November, the website also supports [reviewed audio uploads](voice-input.md):
bounded decoding, interchangeable transcription/translation providers and explicit
confirmation before home/note updates. The earlier text-only scope below describes
the original release. Live WhatsApp, microphone capture and label photos remain absent.

The active app also mounts an authenticated development-only mock messaging API.
See [mock WhatsApp architecture and contract](mock-whatsapp.md) for normalized
events, interchangeable adapters, inbox/outbox durability, and future live-provider
boundaries. This simulator does not satisfy the live WhatsApp contest requirement.

The existing flow document is the journey specification. Direct user instructions
override its channel requirements: the deployed app is web-only and text-only.
The contest PDF explicitly judges WhatsApp and asks for voice/photo; those contest
criteria are not satisfied by this deliberately narrower entry.

## Application and persistence

React 19 + strict TypeScript + Vite, served by the same FastAPI origin. CSS draws
the TV scenes, so no third-party image or font requests are required. Responsive
layouts, keyboard focus, reduced-motion preferences and print styles are included.

SQLite is a deliberate single-store, single-service deployment choice. Every
mutation uses a short BEGIN IMMEDIATE transaction, parameterized queries and an
audit event. Customer serial allocation and stock decrement are serialized.
Optimistic customer/product versions reject stale edits. No network call is made
inside a database transaction. Place data on a persistent local disk; do not use
a network filesystem or scale service replicas without migrating persistence and
reindex locking. The previous PostgreSQL/channel scaffold remains unserved in
`app/legacy.py` only for adapter regression tests.

## Journey and commercial rules

`app/web/flow.py` derives the current conversational prompt and typed reply buttons
from the saved customer record. GET presentation is read-only. Action replies save
an assistant prompt with button metadata, while the browser uses current server
state to enable only the latest actions. Exact text commands share those action
handlers. An explicitly requested single-field home answer can advance without an
AI call; multi-fact notes use structured home extraction. Expert interruptions keep
the saved stage, and End visit records the stage to resume. Inline inputs still
submit the same validated actions, including version and business preconditions.

Home fields can be extracted from text but require human confirmation. Unknown is
an explicit valid answer. The associate controls spending range and final choice.
Recommendations filter available stock within the recorded budget and rank by
refresh, daylight brightness and side seating. Comparison has a separate grounded
AI verdict. Model output never executes a workflow action.

Offers unlock after confirmed assessment and an actual demo with preference and
reason. Quote arithmetic, dated eligibility and finance calculations are Python
rules. Full payment and finance offers cannot stack. Specialist charges stay
unconfirmed until an admin approves a value. A blocking expert question holds
payment/sale until it is resolved. Sale is an explicit action, checks stock and
confirmed amount, decrements one unit atomically and freezes the quote. Delivery,
installation and picture/sound/devices/satisfaction check have separate owned tasks.

## Knowledge and retrieval

1. Admin-managed stable TV specifications and approved store procedures are
   chunked with stable references. `docs/store-knowledge.md` is a review export.
2. Reindex snapshots the stable content, calls `text-embedding-3-small`, verifies
   the content fingerprint has not changed, and publishes a new index atomically.
   A failed build retains the previous index. This is reindexing, not fine-tuning.
3. A structured query optimizer resolves the question using the last 12 messages,
   the selected models and the home card. Unrelated requests get a scope response.
4. BM25 uses positive IDF, length normalization and Unicode tokenization. Vector
   search uses cosine similarity. Reciprocal rank fusion combines the rankings.
5. The answer model sees retrieved passages, the last 16 messages and a separate
   live commercial context. It must return at most three lines and valid source
   IDs. Missing support uses `Not enough facts present.`

Price, stock, arrival dates, offers, charges and finance NEVER enter generated
product chunks. They are read from editable records at each request. A stable
edit marks vectors dirty; retrieval then uses current BM25 facts until rebuild,
visibly reporting its degraded mode. An embedding query outage also reports BM25
fallback. There is no pretend vector backend and no silent fabricated AI answer.

## Security boundaries

Passwords use salted scrypt. Session tokens are opaque random values, stored only
as hashes, expire after 12 hours and live in HttpOnly SameSite=Strict cookies.
Roles come from saved accounts; phone input alone grants no access. Ownership is
checked on private resources. Writes enforce same-origin browser requests, input
schemas, rate limits, workflow preconditions and optimistic versions. Secrets
stay server-side. No model has tools or permission to change records.

User text, history and retrieved content are treated as untrusted. Obvious
instruction-extraction attacks are blocked before a model call; index publication
rejects instruction-like content. Citations are checked against returned sources.
These are defenses, not a proof that all jailbreaks or unsupported model claims
are impossible. Grounding is still probabilistic and needs a larger adversarial
evaluation before real customer rollout. No automatic publication of admin
answers into approved knowledge occurs.

Share URLs carry unguessable bearer tokens, expire in seven days, and can be
revoked. Creation requires explicit consent and confirmation of the current
preview version. Snapshots omit internal chat, notes and private task details.
Later visit edits label existing snapshots outdated. Anyone possessing a link
can read it until expiry/revocation. Do not put real personal data in this demo.

## Operations and limits

The in-process reminder loop persists one reminder at 2 minutes and an escalation
at 5 minutes per unanswered cycle, checked every 30 seconds and on bootstrap.
It catches up after restart. Notifications are browser-polled every 30 seconds;
no external messages are sent. There is one seeded admin, so escalation notifies
the manager queue rather than promising an unavailable second admin.

Use HTTPS with COOKIE_SECURE=true and PUBLIC_ORIGIN set. DEMO_MODE=false rejects
seeded passwords; provision strong account passwords on first start or rotate
existing accounts using the supplied local operator command. Current seeded
accounts are for the contest only; production identity/OTP, multi-store tenancy,
database backups, load testing and adversarial evaluation remain deployment work.

PDFs are server generated from saved data, not model prose. English content is
supported by bundled PDF fonts; original Indic script is best exported using the
browser's print-to-PDF view until multilingual font shaping is integrated.

Official API references used during implementation:
[Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[embeddings](https://developers.openai.com/api/docs/guides/embeddings).
