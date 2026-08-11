# IronMan Recovery V1

This parallel app supports two voice loops over the same orchestrator:

`Siri Dictate Text -> POST /command -> Iron Man reply -> Siri Speak Text`

`iPhone browser microphone -> Vertex AI Gemini Live -> Iron Man tool -> spoken reply`

It does not import or modify the existing Iron Man application.

## Run locally

From the repository root:

```bash
python3 -m venv IronMan_Recovery/.venv
source IronMan_Recovery/.venv/bin/activate
pip install -r IronMan_Recovery/requirements.txt

export IRONMAN_API_TOKEN="replace-with-a-long-random-token"
export ANTHROPIC_API_KEY="replace-with-your-key"
python -m uvicorn IronMan_Recovery.app:app --host 0.0.0.0 --port 8000
```

`ANTHROPIC_API_KEY` is optional for connection testing. Without it, the orchestrator returns a deterministic acknowledgement so the complete Siri round trip can still be verified.

Test the endpoint:

```bash
curl -sS http://127.0.0.1:8000/command \
  -H "Authorization: Bearer replace-with-a-long-random-token" \
  -H "Content-Type: application/json" \
  -d '{"text":"Give me a short status report","session_id":"iphone"}'
```

The response contract is intentionally small:

```json
{
  "status": "ok",
  "reply": "Understood, Niyas. I heard: Give me a short status report",
  "speak": "Understood, Niyas. I heard: Give me a short status report"
}
```

The backend keeps the latest eight user/assistant turns for each `session_id`. Saying `stop`, `exit`, `bye`, or `offline` clears that session and returns exactly `Iron Man offline.`

## Build the Siri Shortcut

Create a shortcut named **Iron Man Voice**. Its backend URL must be reachable from the iPhone; use HTTPS outside a trusted local network.

1. Add **Repeat** and set it to `5`.
2. Inside Repeat, add **Dictate Text**. Choose English and **Stop Listening: After Pause**.
3. Add **If** Dictated Text has any value. Leave the empty branch to stop the shortcut.
4. Add **Get Contents of URL** with `https://YOUR-BACKEND/command`.
5. Select `POST`, request body `JSON`, and add:
   - `text`: Dictated Text
   - `session_id`: `iphone`
6. Add request headers:
   - `Authorization`: `Bearer YOUR_IRONMAN_API_TOKEN`
   - `Content-Type`: `application/json`
7. From **Contents of URL**, get dictionary value `reply` and pass only that value to **Speak Text**.
8. Get dictionary value `status`. If it equals `offline`, add **Stop This Shortcut**.

`/command` is the canonical Siri endpoint. For existing shortcuts, `/api/voice/command` and `/api/iron-man/voice` are compatibility aliases and accept `text`, `transcript`, or `command` as the input key. Production rejects requests when `IRONMAN_API_TOKEN` is not mounted; the local bypass is explicit via `IRONMAN_ALLOW_INSECURE_LOCAL=true`.

## Use live Realtime voice

Open `https://YOUR-BACKEND/voice` in Safari, enter the private Iron Man token once,
and tap **Start voice**. The page stores that token only in the iPhone browser and
never embeds it in source. iOS requires the first microphone start to be a user tap.

Gemini Live on Vertex AI is only the conversational audio interface. Its private
function tool calls the existing Iron Man orchestrator, so Iron Man remains
responsible for answering and executing requests. The server caps each live
session at 15 minutes and allows one live session per Cloud Run instance.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `IRONMAN_API_TOKEN` | empty | Enables Bearer authentication when set. |
| `GOOGLE_CLOUD_PROJECT_ID` | empty | Vertex AI project used for Gemini Live. |
| `GEMINI_LIVE_LOCATION` | `global` | Vertex AI location for Gemini Live. |
| `GEMINI_LIVE_MODEL` | `gemini-live-2.5-flash-native-audio` | Gemini Live model. |
| `GEMINI_LIVE_VOICE` | `Aoede` | Gemini Live voice. |
| `GEMINI_LIVE_MAX_SECONDS` | `900` | Maximum length of one browser voice session. |
| `GEMINI_LIVE_MAX_ACTIVE_SESSIONS` | `1` | Concurrent live sessions allowed per instance. |
| `ANTHROPIC_API_KEY` | empty | Enables live language-model responses. |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Selects the configured Anthropic model. |
| `IRONMAN_MEMORY_TURNS` | `8` | Maximum stored messages per session. |
| `LLM_MAX_TOKENS` | `500` | Maximum spoken-response generation budget. |
| `LLM_TEMPERATURE` | `0.2` | Response variability from 0 to 1. |

## Verify

After installing the recovery requirements, run:

```bash
python -m unittest IronMan_Recovery.test_recovery -v
```

## Deploy through GitHub Actions and Cloud Run

The production target is a separate service named `ironman-recovery` in project `project-2228bebf-326d-4183-a0d`, region `me-central1`. It does not replace the existing Iron Man services.

One time only, open Google Cloud Shell while signed into the project owner account and run:

```bash
bash IronMan_Recovery/setup_gcp.sh
```

The setup script:

- verifies the exact project number before making changes;
- enables the required APIs;
- creates a dedicated GitHub deployment identity;
- configures repository-restricted Workload Identity Federation;
- reuses the existing `ironman-core-runtime` service account and `ironman-api-token` secret; and
- creates no downloadable service-account key.

Before the first Gemini Live deployment, configure the Vertex AI environment:

```bash
bash IronMan_Recovery/configure_realtime.sh
```

The script does not ask for or create an API key. Vertex AI uses the Cloud Run
runtime service account, which receives only the Vertex AI User role.

After IAM has had five minutes to propagate, merging the recovery pull request into `main` runs tests and deploys automatically. The workflow verifies that the public `/command` route returns `401` without the bearer token.

To retrieve the existing token privately in Cloud Shell for the iPhone Shortcut, run:

```bash
gcloud secrets versions access latest \
  --secret=ironman-api-token \
  --project=project-2228bebf-326d-4183-a0d
```

Do not paste the resulting value into GitHub, an issue, a pull request, or chat. Put it only in your private Jellycuts source or Apple Shortcut.

This version deliberately excludes SIP, Pushcut, and shortcut signing. Gemini Live
audio uses a browser WebSocket bridge; cloud deployment adds no Google Cloud SDK to
the application container.
