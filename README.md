# Iron Man V2

Iron Man V2 keeps Iron Man as the orchestration layer and moves execution behind
capability-based backends. The primary backend is Antigravity, with a local
deterministic fallback until credentials are configured. The deployment target
is Google Cloud Run.

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Useful endpoints:

- `GET /` - service status.
- `POST /api/iron-man/tasks` - create and route a task.
- `GET /api/system/capabilities` - list capability contracts.
- `GET /api/system/migration/gcp` - GCP migration readiness.
- `GET /api/system/legacy-blueprint` - recovered Thor/Loki operating rules for Iron Man V2.
- `POST /api/voice/sessions` - open a realtime transcript-first voice session.
- `GET /api/shortcuts/ask-iron-man.jelly` - ready-to-paste Jellycuts source for the iPhone voice shortcut.

## Recovered Thor/Loki Blueprint

The earlier Thor/Loki files are preserved as design lineage:

- Iron Man is the single coordinator the user talks to.
- Loki is the first specialist pattern for documents, coding, operations, shortcuts, and validation.
- Voice, Shortcuts, Jellycuts, web, Mac, and container interfaces are adapters around the core.
- External writes, sends, deletes, imports, installs, signing, publishing, payments, and irreversible changes must pause for explicit approval.
- The system reports implemented and planned features separately.

## Configure Antigravity

```bash
export ANTIGRAVITY_ENDPOINT="https://your-antigravity-endpoint"
export ANTIGRAVITY_API_KEY="your-secret"
export EXECUTION_BACKEND="antigravity"
```

Without these values, Iron Man still accepts work and records the execution route
using the local fallback.

## Deploy To Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/iron-man-v2:latest
gcloud run services replace deploy/cloudrun.service.yaml --region us-central1
```

Replace `PROJECT_ID` in `deploy/cloudrun.service.yaml` before deployment. Live
deployment requires GCP project permissions and service account access.

## Shortcut Signing Service (macOS only)

Wraps Apple's `shortcuts sign` command-line tool as an HTTP endpoint the
main backend calls to turn an unsigned `.shortcut` file into one iOS will
actually import.

**This cannot run on Linux/Windows/the sandbox this project was built
in.** It requires real macOS (Monterey 12+) because `shortcuts sign` is
part of the macOS Shortcuts app, and there is no public Apple API for
signing -- Linux/Windows have no equivalent tool.

## Setup (on a Mac)

```bash
cd macos_signing_service
pip3 install -r requirements.txt --break-system-packages
python3 app.py            # listens on :5005
```

Sign in to iCloud on this Mac first (`--mode anyone` notarizes through
Apple's servers, which requires it).

## Wire it up to the main backend

On the machine running the main FastAPI backend:

```bash
export SHORTCUT_SIGNING_SERVICE_URL="http://<this-macs-ip>:5005"
# optional shared-secret auth between the two services:
export SHORTCUT_SIGNING_SERVICE_API_KEY="something-long-and-random"
```

Then `POST /api/export-shortcut` on the main backend will automatically
route the generated file through this service and return a **signed**
file. If this service is unreachable, the main backend degrades
gracefully -- it still returns a file, just an unsigned one, with a
warning explaining why (see `X-Shortcut-Signed` response header).

## Deployment options for the Mac itself

You need *some* real Mac reachable over HTTP by your backend, 24/7 if you
want this to work for arbitrary users at any time:

- **Your own Mac / a Mac mini**, port-forwarded or tunneled (e.g. via
  Tailscale or ngrok) to your backend server. Cheapest option if you
  already own one; not great uptime guarantees.
- **Cloud Mac hosting** (MacStadium, MacinCloud, AWS EC2 Mac instances).
  Real 24/7 uptime, but meaningfully more expensive than typical Linux
  hosting (Apple's EULA requires dedicated hardware, not shared VMs).
- **CI-triggered signing** (e.g. a macOS GitHub Actions runner invoked
  per-request) -- works, but adds several seconds of cold-start latency
  per shortcut generated, and GitHub Actions macOS minutes are billed at
  a premium.

## Things to verify before relying on this in production

I built and reviewed this against Apple's own CLI documentation, but
could not test the actual `shortcuts sign` execution myself (no macOS
available in the environment this was built in). Please verify on a
real Mac + real iPhone before shipping:

1. Run `shortcuts sign --mode anyone --input test.shortcut --output
   test-signed.shortcut` manually once and confirm the output actually
   imports on an iPhone.
2. There are scattered developer reports of `shortcuts sign` exiting
   successfully (code 0) without actually producing a validly signed
   file. If you hit that, the community-maintained
   [scaxyz/shortcut-signing-server](https://github.com/scaxyz/shortcut-signing-server)
   (Go, same underlying approach, more battle-tested) is a solid
   alternative reference implementation.
3. `--mode anyone` uploads the shortcut content to Apple for validation
   -- don't sign files containing real API keys/secrets this way; keep
   secrets as user-filled placeholders instead (which is how the main
   backend already generates URLs -- see `WFURL` placeholders).
