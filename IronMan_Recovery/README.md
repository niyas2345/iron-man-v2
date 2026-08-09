# IronMan Recovery V1

This parallel app restores the smallest reliable voice loop:

`Siri Dictate Text -> POST /command -> Iron Man reply -> Siri Speak Text`

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

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `IRONMAN_API_TOKEN` | empty | Enables Bearer authentication when set. |
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

After IAM has had five minutes to propagate, merging the recovery pull request into `main` runs tests and deploys automatically. The workflow verifies that the public `/command` route returns `401` without the bearer token.

To retrieve the existing token privately in Cloud Shell for the iPhone Shortcut, run:

```bash
gcloud secrets versions access latest \
  --secret=ironman-api-token \
  --project=project-2228bebf-326d-4183-a0d
```

Do not paste the resulting value into GitHub, an issue, a pull request, or chat. Put it only in your private Jellycuts source or Apple Shortcut.

V1 deliberately excludes WebSockets, Pushcut, audio streaming, and shortcut signing. Cloud deployment files package the same minimal HTTP runtime without adding cloud SDKs to the application.
