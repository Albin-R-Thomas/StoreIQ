# Initial API contract

> Archived scaffold contract. These channel routes are not mounted by the current
> application. Use [web-api-contract.md](web-api-contract.md) and the generated
> `postman/specs/store-iq.openapi.json` for the shipped text-only website.

This is a development scaffold. FastAPI routes and Pydantic schemas are the source
of truth; `/openapi.json` and `/docs` expose the executable contract.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health/live` | Process liveness; no database access |
| GET | `/health/ready` | Database connectivity |
| POST | `/api/v1/sessions` | Create an associate's customer interaction |
| GET | `/api/v1/sessions/{id}` | Read session metadata |
| GET | `/api/v1/sessions/{id}/messages` | Read a paginated conversation |
| POST | `/api/v1/sessions/{id}/messages` | Submit text through the coaching service |
| POST | `/api/v1/dev/mock-recordings` | Submit `mock_recording_text` through the same service |
| POST | `/api/v1/dev/mock-whatsapp-text` | Simulate a WhatsApp text conversation and reply |
| POST | `/api/v1/dev/retrieval/search` | Inspect BM25 hits without a database or AI call |
| GET | `/api/v1/meta/webhook` | Meta subscription challenge |
| POST | `/api/v1/meta/webhook` | Verify and durably ingest WhatsApp messages |
| POST | `/api/v1/dev/meta/send-text` | Exercise mock or allowlisted test WhatsApp delivery |

Sessions and messages use UUIDs. Lists use `limit` (1-100) and `offset` (>=0).
Session creation and successful coaching return 201. Missing sessions return 404;
invalid input returns 422; unavailable adapters/configuration return 503;
upstream integration failures return 502. Coaching saves input and reply in one
transaction after the AI succeeds. Sending to Meta is an explicit separate action.

`mock_recording_text` substitutes only for speech transcription. It uses the
configured AI adapter, so it is deterministic with `AI_PROVIDER=mock` and makes a
paid provider request with `AI_PROVIDER=openai`. Development routes are enabled by
default and can be disabled with `ENABLE_DEV_ROUTES=false`.

All coaching inputs (plain text, mock recording, mock WhatsApp text) retrieve
knowledge before invoking AI. Responses include `knowledge` with retrieval status,
source IDs, chunk text, BM25 scores and mock provenance. The same trace is saved in
the assistant message's JSON details. BM25 scores express lexical relevance, not
confidence or factual verification. Catalog facts remain a separate dependency.

The WhatsApp mock accepts `session_id`, `mock_whatsapp_text`, and an optional
`sender` test phone number. It creates and normalizes a WhatsApp-shaped text
message, runs coaching, persists the exchange and returns `inbound`, `coaching`,
and `outbound`. Outbound is always simulated, even with `META_MODE=live`; it does
not invoke the Meta client or enqueue a real webhook. AI still uses `AI_PROVIDER`.
Each call creates a new test message. This route does not exercise webhook
signatures, inbox deduplication or a real WhatsApp delivery.

Retrieval search accepts `query`, `store_id`, and `top_k` (1-10, optional). Only
global documents and documents scoped to that store are scored. A missing or
invalid configured corpus returns 503; empty corpora and unmatched queries return
200 with no hits. `RAG_PROVIDER=disabled` explicitly disables retrieval. The JSON
corpus is loaded once per process; restart after edits.

Webhook POSTs require `X-Hub-Signature-256`, calculated over the exact raw body with
`META_APP_SECRET`. The inbox deduplicates by business phone number ID and WhatsApp
message ID. Authenticated status notifications and unsupported event objects are
acknowledged and ignored. Incoming text, audio, and image payloads are retained;
ingestion does **not** invoke AI or send a reply. A worker is a future module.

No associate authentication/authorization or production deployment is included.
Local host ports bind to 127.0.0.1. Only test data and test numbers belong here.
