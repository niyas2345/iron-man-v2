#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="project-2228bebf-326d-4183-a0d"
REGION="me-central1"
SERVICE="ironman-recovery"
MODEL="${GEMINI_LIVE_MODEL:-gemini-live-2.5-flash-native-audio}"
MAX_SECONDS="${GEMINI_LIVE_MAX_SECONDS:-900}"
MAX_ACTIVE="${GEMINI_LIVE_MAX_ACTIVE_SESSIONS:-1}"

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "Reopen Cloud Shell and authorize it first." >&2
  exit 1
fi

gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud run services update "${SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --update-env-vars="GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID},GEMINI_LIVE_LOCATION=global,GEMINI_LIVE_MODEL=${MODEL},GEMINI_LIVE_VOICE=Aoede,GEMINI_LIVE_MAX_SECONDS=${MAX_SECONDS},GEMINI_LIVE_MAX_ACTIVE_SESSIONS=${MAX_ACTIVE}" \
  --quiet

echo "Gemini Live settings updated on ${SERVICE}; no API key or secret was changed."
