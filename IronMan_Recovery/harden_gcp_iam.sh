#!/usr/bin/env bash
set -euo pipefail

# Reconcile only IronMan's bearer-token secret. No secret value is printed.
PROJECT_ID="project-2228bebf-326d-4183-a0d"
PROJECT_NUMBER="761020604913"
REGION="me-central1"
SERVICE="ironman-recovery"
SECRET="ironman-api-token"
SECRET_VERSION="4"
RUNTIME_SERVICE_ACCOUNT="ironman-core-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
DEPLOYER_SERVICE_ACCOUNT="github-ironman-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

REQUIRED_ACCESSORS=(
  "serviceAccount:${RUNTIME_SERVICE_ACCOUNT}"
  "serviceAccount:${DEPLOYER_SERVICE_ACCOUNT}"
)

# These principals are unrelated to the IronMan bearer-token secret.
# This does not alter Developer Connect's own regional OAuth secret.
REMOVE_DIRECT_ACCESS=(
  "user:abdeenniyas23@gmail.com"
  "serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-devconnect.iam.gserviceaccount.com"
)

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "No active Google Cloud account. Reopen Cloud Shell and authorize it." >&2
  exit 1
fi

ACTUAL_PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
if [[ "${ACTUAL_PROJECT_NUMBER}" != "${PROJECT_NUMBER}" ]]; then
  echo "Project identity check failed; no changes were made." >&2
  exit 1
fi

gcloud config set project "${PROJECT_ID}" >/dev/null

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT
BEFORE_POLICY="${WORK_DIR}/before.json"
AFTER_POLICY="${WORK_DIR}/after.json"
BACKUP_POLICY="${PWD}/ironman-secret-iam-backup-$(date -u +%Y%m%dT%H%M%SZ).json"

gcloud secrets get-iam-policy "${SECRET}" --project="${PROJECT_ID}" --format=json >"${BEFORE_POLICY}"
cp "${BEFORE_POLICY}" "${BACKUP_POLICY}"

python3 - "${BEFORE_POLICY}" "${AFTER_POLICY}" "${REMOVE_DIRECT_ACCESS[@]}" <<'PY'
import json
import sys

source, destination, *members_to_remove = sys.argv[1:]
with open(source, encoding="utf-8") as handle:
    policy = json.load(handle)

blocked = set(members_to_remove)
bindings = []
for binding in policy.get("bindings", []):
    members = [member for member in binding.get("members", []) if member not in blocked]
    if members:
        binding["members"] = members
        bindings.append(binding)
policy["bindings"] = bindings

with open(destination, "w", encoding="utf-8") as handle:
    json.dump(policy, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

if ! cmp -s "${BEFORE_POLICY}" "${AFTER_POLICY}"; then
  gcloud secrets set-iam-policy "${SECRET}" "${AFTER_POLICY}" \
    --project="${PROJECT_ID}" --quiet >/dev/null
fi

for MEMBER in "${REQUIRED_ACCESSORS[@]}"; do
  # Remove an overly broad project-level accessor grant, if one exists.
  gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet >/dev/null 2>&1 || true

  # Grant access only on the single IronMan token secret.
  gcloud secrets add-iam-policy-binding "${SECRET}" \
    --project="${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet >/dev/null
done

gcloud run services update "${SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --update-secrets="IRONMAN_API_TOKEN=${SECRET}:${SECRET_VERSION}" \
  --quiet >/dev/null

SERVICE_URL="$(gcloud run services describe "${SERVICE}" \
  --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
TOKEN="$(gcloud secrets versions access "${SECRET_VERSION}" \
  --project="${PROJECT_ID}" --secret="${SECRET}")"

AUTH_STATUS="$(curl --silent --output "${WORK_DIR}/authorized.json" --write-out '%{http_code}' \
  --request POST "${SERVICE_URL}/command" \
  --header "Authorization: Bearer ${TOKEN}" \
  --header 'Content-Type: application/json' \
  --data '{"text":"security verification","session_id":"gcp-hardening"}')"
unset TOKEN

UNAUTH_STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --request POST "${SERVICE_URL}/command" \
  --header 'Content-Type: application/json' \
  --data '{"text":"security verification","session_id":"gcp-hardening"}')"

if [[ "${AUTH_STATUS}" != "200" || "${UNAUTH_STATUS}" != "401" ]]; then
  echo "Verification failed: authorized=${AUTH_STATUS}, unauthorized=${UNAUTH_STATUS}." >&2
  exit 1
fi

echo "IronMan IAM hardening complete."
echo "Authorized request: HTTP ${AUTH_STATUS}; unauthorized request: HTTP ${UNAUTH_STATUS}."
echo "Cloud Run is pinned to ${SECRET}:${SECRET_VERSION}."
echo "IAM backup: ${BACKUP_POLICY}"
