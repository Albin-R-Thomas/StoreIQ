# Azure voice POC setup and decision

Decision: 5 November 2026. Use **Azure Speech Translation** for the initial audio
session. This supersedes the proposed Deepgram transcription + Azure Translator
sequence, which was not implemented. The aim is to remove the application's second
sequential translation call, not to claim a latency improvement without measuring it.

## Required from you

1. Sign in to the [Azure portal](https://portal.azure.com/), select your subscription
   and create a **Speech** resource. Choose **F0 (Free)** if available. Record the
   exact region identifier shown in **Keys and Endpoint** (for example
   `centralindia`, only if that is the actual resource region).
2. Copy **Key 1 or Key 2** from that Speech resource into the local `.env` as
   `AZURE_SPEECH_KEY`. Set `AZURE_SPEECH_REGION` to its region identifier.
3. Keep `VOICE_PROVIDER=azure` and `VOICE_TRANSLATION_PROVIDER=azure`. Restart the
   backend after editing `.env`; settings are cached. Do not paste keys into chat,
   commit them, or place them in frontend environment variables.

```dotenv
VOICE_PROVIDER=azure
VOICE_TRANSLATION_PROVIDER=azure
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
```

Only these Speech credentials are required to upload audio, receive the original
transcript and selected translation, and prepare unchanged text. Keep original
only uses Azure transcription without a translation target. Home assessment
extraction still requires the existing `OPENAI_API_KEY` and `AI_MODEL`; changing
the speech provider does not migrate chat, embeddings or structured extraction.

## Optional: translate corrections or change target after upload

Speech translates audio, not an arbitrarily edited transcript. For that review
operation, create a separate **Translator** resource on **F0 (Free)** and collect:

```dotenv
AZURE_TRANSLATOR_KEY=
AZURE_TRANSLATOR_REGION=
```

Use Key 1 or Key 2 from the **Translator** resource. This is not the Speech key.
For a regional resource, set its exact location; for a global Translator resource,
leave region blank. The adapter uses the public global text endpoint:
`https://api.cognitive.microsofttranslator.com/translate?api-version=3.0`.
Private endpoints and sovereign-cloud endpoints are outside this POC configuration.

No text request occurs during the initial combined Speech session or an unchanged
preview. If the optional key is absent, edited-text translation fails explicitly;
choose **Keep original only** to continue without translation. No automatic paid
fallback occurs.

## Quotas and verification

As checked on 5 November 2026, [Speech F0 pricing](https://azure.microsoft.com/en-us/pricing/details/speech/)
lists 5 audio hours/month for standard speech translation. The separate
[Translator F0 tier](https://azure.microsoft.com/en-us/pricing/details/translator/)
lists 2 million characters/month. Resource availability and concurrency limits
apply; check the selected resource in the portal. This implementation does not
upgrade plans or create Azure resources.

After configuring keys, restart the backend and use **Record voice note** beside
Send. Allow microphone access, speak, then press Stop. The UI automatically detects the input language and always requests English.
Review the English text in the message box, then explicitly Send. Repeat with
English, Hindi and Marathi,
including numbers, units and product names. Record elapsed time and human-reviewed
accuracy. The user has reported transcription/translation working; agent-measured
Azure latency and broader language accuracy checks remain pending.

An isolated CLI check using only Speech credentials (no active customer DB):

```powershell
.venv/Scripts/python.exe -m scripts.check_voice --audio path/to/synthetic.wav --live --speech-only --source en
```

This reports upload latency, transcript and translation and saves an unchanged
synthetic visit note. Omit `--speech-only` for the full home-extraction and changed
translation-target check, which also needs Translator and existing OpenAI keys.

The combined SDK uses continuous recognition to collect all final segments of
files up to 120 seconds. Automatic source identification is restricted to English,
Hindi and Marathi at session start; code-switching quality remains unverified.
Normalized audio goes to Azure Speech; edited text goes to Azure Translator only
when requested. Raw audio is not persisted in the application database.

## Contract references

- [Speech translation SDK and audio-file input](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-translate-speech)
- [Speech language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
- [Translator authentication](https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/reference/authentication)
- [Voice workflow and adapter details](voice-input.md)

Provider selection is internal. Public upload/review/confirmation routes are
unchanged. `CombinedSpeechProvider` returns a `SpeechResult` containing the
original `Transcript` and optional `Translation`; other speech adapters can still
use the existing separate transcription and translation protocols.
