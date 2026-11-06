# Store IQ text fixes and final acceptance

**PASS for the tested backend text scope.** The associate journey now completes through text without manually submitting site, sale, follow-up, task or share forms. The server is running at **http://127.0.0.1:8012**, using a separate synthetic acceptance database. Existing working data was preserved.

This closes the text/backend findings from [the original audit](contest-final-acceptance-audit-2026-11-05.md). New photo input was excluded by the user's explicit instruction. Live WhatsApp integration and replacement of synthetic commercial/catalogue data remain deferred. Contest use must still use test people and approved test data.

## What changed

| Original finding | Resolution |
|---|---|
| Slow, silent AI requests | Completed replies return 200; work taking longer than 1.5 seconds returns a durable 202 acknowledgement. Authenticated polling returns the final answer or retryable failure. The website handles polling. |
| Site-check text discarded | Saved, interruptible input collection asks one missing check at a time. Explicit combined site answers are accepted together. Unknown or unchecked evidence holds the final total. |
| Form-dependent completion | Text now captures extras, explicit amount confirmation, consented recipient/PDF preview, follow-up reason/permission/time/owner, task evidence and installation problems. These share the existing validated business services. |
| Customer list did not select a serial | Date choices, paging and serial selection are handled in backend text. The result returns the selected customer's ID and saved journey. New customers retain separate permanent serials and duplicate-name suffixes. |
| Unknown model treated as unrelated | Unknown typed model IDs return the required missing-facts response without inventing a replacement specification. |
| Marathi next-question failure | The known next assessment question is answered locally in the selected language; Hindi/Marathi belief intents use language-aware classification. |
| Chat cost lacked itemisation | Charge details are available in chat, in groups of at most three logical lines, with required and optional totals and unknown details. |
| Overgenerous coaching score | Sourced Validate/Translate answers earn partial credit; full credit requires recorded customer-response evidence. Review advice identifies a specific missing behavior. |
| Missing shift conversation | Start asks for the department; TV returns a current-data brief. Missing daily change logs and video are disclosed rather than invented. |
| Request IDs silently discarded different text | Conflicting content under an existing request ID returns 409. Exact retries reuse their result without repeating sale, stock or task effects. |
| Runtime voice failures | Installed the declared Azure Speech dependency and added a packaged FFmpeg fallback for supported desktop platforms. The existing voice adapters were retained. |

Explicit small budgets are also preserved: **INR 100 is never silently multiplied into INR 100,000**. Devanagari digits and explicit thousand/lakh units are normalized for matching.

## Final validation

| Check | Result |
|---|---|
| Full regression suite | **88 passed**, zero failures/errors, **63.257 seconds** |
| Real HTTP acceptance | **94 observations**, including **75 text messages**, all scenario assertions passed |
| Five simultaneous real text requests | All saved the requested distance; **0.248-0.255 seconds** |
| Local Postman provider outage | Passed; provider 503 maps to 502, one retained user message, no fabricated answer or duplicate retry |
| Production frontend build | TypeScript and Vite build passed |
| Changed-code lint | Passed with the repository's pre-existing long-string E501 violations excluded |
| OpenAPI | Regenerated with the 202 receipt and result-polling route |

The HTTP journey used the configured real AI provider and a fresh hybrid index. Business-action checks inspected resulting saved records, not just HTTP status. The provider outage check separately used the existing local Postman stand-in.

### Latency

| Measurement | Seconds |
|---|---:|
| Text first reply p50 | **0.046** |
| Text first reply p95 | **1.521** |
| Text first reply maximum | **1.546** |
| Slowest final AI answer in the run | **10.448** |

All 75 first replies were under five seconds. Five slow requests returned an acknowledgement before the final answer. These are separate measurements: **the final AI answer is not promised within five seconds**. Percentiles use nearest rank over localhost; five concurrent explicit text answers establish that sampled workload, not a sustained store-scale load benchmark.

### Journey exercised

1. Sign in; start shift; select TV and receive the brief.
2. Reject early finance; extract seven natural home facts; confirm the home; recommend three options.
3. Correct a 4K belief with sources; explain HDMI for this home; record what the customer understood.
4. Read comparison details; record a demo preference and reason without creating a sale.
5. Complete the site check through text; add/remove optional soundbar; review eligible offer and finance arithmetic.
6. Ask for explicit sale confirmation and confirm the displayed amount. Replay the same sale request without duplicate tasks.
7. Decline sharing, verify the hold, then grant consent; preview a test recipient/PDF, confirm simulated sharing and download the actual PDF.
8. Complete delivery, installation and working check through text; inspect closed stage and evidence-based seven-step score.
9. Report a later installation problem; verify handover reopens and dependent working-check completion is invalidated. Revoke the share link.
10. Start another customer; save an internal follow-up with owner/time and no contact permission; end/resume the visit through the serial list.
11. Reject an unknown model; return missing-facts fallback for an unsupported specification; escalate to admin and verify the attributed reply remains in the original customer chat.
12. Exercise Hindi belief correction, Marathi next-question handling and injection blocking, then run simultaneous text requests.

The recorded internal 14/14 means the supplied test evidence satisfied the application's scorer. Backend probes record associate demo confirmations; they do not physically demonstrate a television or establish the judges' score.

## Voice and Marathi clarification

Voice input and Marathi support were already integrated. The chat recorder uses auto language detection and translates into English for review before Send. The dedicated voice API supports English, Hindi and Marathi targets.

The existing Azure path now passed **live synthetic Marathi recording tests**:

- Auto source to English: **200**, **7.000 seconds**. Translation retained cricket, movies, nine-foot distance and sunlight.
- Explicit Marathi source to Marathi: **200**, **6.026 seconds**. Marathi transcript/target text retained cricket.
- Both uploads preserved the visit's home/sale/consent state until a separate reviewed action.

These checks used the existing Speech integration. No new photo or replacement speech integration was added. Synthetic recognition does not establish noisy-shop or code-switching accuracy.

## Evidence and reproduction

All fresh raw evidence is local and gitignored under `output/text-final-acceptance-2026-11-06/`:

- `summary.json`, `http-evidence.json`, `http-run.log`: measured HTTP scenario results, inputs and outputs.
- `regression.log`: final 88-test run.
- `simulation-check.log`, `simulation.ndjson`: provider-outage outcome and transport events.
- `marathi-voice.json`, `synthetic-marathi.wav`: live synthetic voice results and test recording.
- `text-journey-summary.pdf`: downloaded synthetic purchase summary; visual PDF layout was not part of this backend acceptance.

Run against an isolated database because the scenario intentionally records test sales and changes synthetic stock:

```powershell
$env:WEB_DATABASE_PATH = 'output/my-text-acceptance.db'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012
```

In another shell:

```powershell
.venv/Scripts/python.exe -m scripts.final_text_acceptance --live --base-url http://127.0.0.1:8012
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m scripts.check_marathi_voice --live
```

The two `--live` commands make configured-provider calls using synthetic test material. API integrations must handle 202 and poll `status_url`; existing local scenario drivers now include that polling behavior. See [the updated API contract](web-api-contract.md) and [voice details](voice-input.md).

The revised text scope is accepted on this evidence. Live WhatsApp delivery, approved data replacement, human floor usability and the contest's independent judging remain separate acceptance activities; new photo input remains excluded by request.
