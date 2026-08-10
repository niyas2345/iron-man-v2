#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="project-2228bebf-326d-4183-a0d"
RUNTIME_SERVICE_ACCOUNT="ironman-core-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
DEPLOYER_SERVICE_ACCOUNT="github-ironman-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
OPENAI_SECRET="openai-api-key"

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "Reopen Cloud Shell and authorize it first." >&2
  exit 1
fi

gcloud config set project "${PROJECT_ID}" >/dev/null
read -r -s -p "Paste the OpenAI API key (hidden): " OPENAI_KEY
echo
if [[ -z "${OPENAI_KEY}" ]]; then
  echo "No key entered; nothing changed." >&2
  exit 1
fi

if gcloud secrets describe "${OPENAI_SECRET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  printf '%s' "${OPENAI_KEY}" | gcloud secrets versions add "${OPENAI_SECRET}" \
    --project="${PROJECT_ID}" --data-file=- --quiet
else
  printf '%s' "${OPENAI_KEY}" | gcloud secrets create "${OPENAI_SECRET}" \
    --project="${PROJECT_ID}" --replication-policy=automatic --data-file=- --quiet
fi
unset OPENAI_KEY

for MEMBER in \
  "serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
  "serviceAccount:${DEPLOYER_SERVICE_ACCOUNT}"; do
  gcloud secrets add-iam-policy-binding "${OPENAI_SECRET}" \
    --project="${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet >/dev/null
done

echo "OpenAI Realtime secret configured without printing the key."
