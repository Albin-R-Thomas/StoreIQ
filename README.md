# Store IQ

A TV associate workspace with text and reviewed voice uploads: understand the home, compare the right
screens, demonstrate the difference, quote the complete cost and follow through
until the TV works. Includes an admin console and editable synthetic data.

An authenticated [mock WhatsApp adapter](docs/mock-whatsapp.md) now runs the same
saved journey without a phone number. It provides a durable inbox/outbox and a
provider-neutral interface for future Meta/Twilio adapters. Try it against the
running API with `python -m scripts.try_mock_whatsapp`. No real WhatsApp delivery or
photo integration is enabled. Reviewed audio-file uploads are now available in the
website; see [voice transcription and translation](docs/voice-input.md).
Voice defaults to Azure Speech for combined transcription/translation in one
session. See [Azure keys and POC setup](docs/azure-voice-setup.md); live Azure
validation is pending credentials. Edited-text translation optionally uses Azure
Translator. Chat and home extraction still use the existing OpenAI configuration.

See [implementation status and next steps](docs/implementation-status-and-next-steps.md)
for completed work, pending modules, dependencies and copy-ready implementation prompts.

## Run locally

Python 3.12+ and Node 24+ are required. Your existing `.env` is read without
overwriting its secrets. The current website uses `OPENAI_API_KEY` and `AI_MODEL`
directly; `AI_PROVIDER` and Meta settings belong to the retired channel scaffold.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. API docs: **http://127.0.0.1:8000/docs**.
The optional `scripts/start-web.ps1` performs installation, build and startup.
For frontend hot reload, run `npm.cmd run dev` in `frontend`; API requests proxy
to port 8000. Cookies stay on the browser origin.

| Demo role | Phone | Password |
| --- | --- | --- |
| Associate Aarav | 9000000001 | Associate@123 |
| Associate Meera | 9000000002 | Associate@123 |
| Admin Priya | 9000000009 | Admin@123 |

These are synthetic accounts, active only with `DEMO_MODE=true`. The role is
loaded from the account after password verification. Customers and serial numbers
are separate per associate. No live WhatsApp route is mounted. The chat microphone
records locally, then sends the clip to the existing voice endpoint for English translation.
Authenticated voice-file upload/review routes are available.

## What is implemented

- Shift brief, current stock and scheduled offers; independent saved training
  attempts, feedback, accuracy, repeat practice and revisit topics.
- Persistent customer lists, permanent serials, duplicate-name handling, IST
  activity-date filters and admin associate filters.
- Text chat in English, Hindi and Marathi using the configured OpenAI model,
  home extraction, one missing question at a time, source passages and retry.
- Guided messaging-style prompts with up to three contextual reply buttons:
  shift start, customer selection, home confirmation, recommendations, demo,
  complete cost, payment, consent, tasks and review. Forms open inline in chat;
  exact text commands use the same saved workflow actions.
- Home confirmation, ranked in-stock recommendations, 2–3 TV comparisons and a
  grounded AI verdict. A physical demo requires a preferred TV and reason.
- Itemised quote, optional extras, site check, dated offer eligibility and finance
  with full arithmetic. Unknown charges and blocking expert questions hold closing.
- Explicit synthetic sale confirmation, atomic stock decrement, frozen purchase
  quote and separate delivery, installation and working-check tasks.
- Consent, summary preview, versioned PDF download, expiring share snapshots,
  stale-version warning and revocation. No external delivery occurs.
- Expert requests, deduplication, ownership, attributed admin answers, follow-ups,
  notifications, resolution/reopening and persisted reminder/escalation cycles.
- Conversation and visit-note history; evidence-based seven-step coaching review.
- Friendly admin forms for TV specs, stock, prices, arrivals, dated offers, charges,
  finance and approved knowledge, plus an advanced structured editor.
- Durable SQLite transactions, password hashing, session expiry, ownership checks,
  same-origin writes, rate limiting, input validation and audit events.

## RAG and editable data

Sign in as admin → **Store management** → **Rebuild RAG index**. This builds
embeddings using `text-embedding-3-small` and publishes the index atomically.

The pipeline optimizes each query using conversation history, home details and
selected models, then combines **BM25 + cosine vector retrieval with reciprocal
rank fusion**. Answers expose their sources and retrieval mode. Stable edits mark
the index dirty; current BM25 facts remain usable until the next rebuild.

Stock, prices, offer dates, arrivals, charges and finance terms are read live into
message context; they never enter generated product chunks. Commercial edits need
no index rebuild. Rebuilding is document indexing, not model fine-tuning.

The initial seed has eight synthetic TVs, four store procedure documents, two
dated offers, six practice questions and three test visitors. No fixtures are
official manufacturer specifications. Inspect the review export in
[docs/store-knowledge.md](docs/store-knowledge.md). Regenerate it after approved
edits with `python -m scripts.export_store_knowledge`.

The app does not fabricate a successful AI reply if provider access fails. With
the updated credential, live indexing, text coaching, context follow-up and an AI
comparison verdict have passed using `AI_MODEL=gpt-6-luna`. Missing-fact fallback
and injection blocking also passed the sampled live journey checks. The running
application has a published hybrid index. See validation evidence for scope.

## Checks and API artifacts

The backend text journey now supports site checks, explicit sale confirmation,
follow-up, handover task updates and previewed simulated sharing without forms.
Slow messages acknowledge saved input within 1.5 seconds with HTTP 202; API clients
poll the authenticated `status_url` for the answer. See [the text API contract](docs/web-api-contract.md).
For a live synthetic HTTP acceptance run against a separate server/database:

```powershell
python -m scripts.final_text_acceptance --live --base-url http://127.0.0.1:8012
```

This makes configured-provider calls and records test sales. Use an isolated
database. The bundled audio decoder removes the separate desktop FFmpeg setup
step; Azure Speech remains the existing voice/translation provider.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m scripts.export_openapi
cd frontend
npm.cmd run build
```

The exported [OpenAPI contract](postman/specs/store-iq.openapi.json) is generated
from FastAPI. See [web API behavior](docs/web-api-contract.md),
[architecture and security boundaries](docs/architecture.md) and
[validation evidence](docs/validation.md).

The local Postman simulation exercises the real OpenAI SDK without a real key:

```powershell
# Install once if Postman CLI is not available (desktop Postman is different).
npm.cmd install --prefix .tools/postman postman-cli
node .tools/postman/node_modules/postman-cli/bin/postman.js simulation run postman/simulations/associate-ai.sim.yaml --port 4010 --output ndjson --no-history
# In another terminal:
.\.venv\Scripts\python.exe -m scripts.check_ai_simulation
```

The script uses an isolated temporary database. It checks index construction,
structured parsing, hybrid retrieval, source attribution and a provider outage
with a saved, deduplicated user message. `--live` explicitly checks the configured
real provider instead and makes paid API calls. Do not configure a production
service to use the fixture endpoint.

For a live guided-conversation check using synthetic data and an already published
knowledge index, run `python -m scripts.check_guided_chat --live`. It checks natural
home extraction, the matching buttons, an expert interruption, return to the saved
step and physical-demo gates. This command makes paid OpenAI requests.

## Deployment

```powershell
docker compose up --build -d
```

The multi-stage image builds the frontend, runs as an unprivileged user, serves
the site and API on port 8000, checks readiness and persists SQLite in a named
volume. `compose.legacy.yaml` retains the old unserved PostgreSQL scaffold setup.

Use one application replica with local persistent disk. Before exposing outside a
trusted demo environment, rotate all seeded account passwords, use HTTPS,
`COOKIE_SECURE=true`, `PUBLIC_ORIGIN=https://your-host`, `DEMO_MODE=false`, backup
the database and complete identity, load and adversarial evaluation. To rotate:

```powershell
.\.venv\Scripts\python.exe -m scripts.rotate_web_password 9000000001
```

Passwords are entered through a hidden prompt and existing sessions are revoked.
New non-demo databases require the three password environment variables in
`.env.example`. Startup rejects existing default passwords outside demo mode.

No claim is made that prompt injection can be eliminated completely. Defensive
prompt boundaries, input checks and source validation reduce risk; deterministic
workflow gates keep AI output from executing business actions. Browser visual QA
was blocked by the computer-use runtime. See validation evidence for the exact
checks and deployment limits.
