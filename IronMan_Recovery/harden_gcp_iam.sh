#!/usr/bin/env bash
set -euo pipefail

# Reconcile only IronMan's bearer-token secret. No secret value is printed.
PROJECT_ID="project-2228bebf-326d-4183-a0d"
PROJECT_NUMBER="761020604913"
REGION="me-central1"
SERVICE="ironman-recovery"
SECRET="ironman-api-token"
SECRET_VERSION="4"
ACCESSOR_ROLE="roles/secretmanager.secretAccessor"
STALE_SECRET_VERSIONS=("1" "2" "3")
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
FINAL_POLICY="${WORK_DIR}/final.json"
BACKUP_POLICY="${PWD}/ironman-secret-iam-backup-$(date -u +%Y%m%dT%H%M%SZ).json"

gcloud secrets get-iam-policy "${SECRET}" --project="${PROJECT_ID}" --format=json >"${BEFORE_POLICY}"
cp "${BEFORE_POLICY}" "${BACKUP_POLICY}"

python3 - "${BEFORE_POLICY}" "${AFTER_POLICY}" "${REMOVE_DIRECT_ACCESS[@]}" -- "${REQUIRED_ACCESSORS[@]}" <<'PY'
import json
import sys

source, destination = sys.argv[1:3]
separator = sys.argv.index("--")
members_to_remove = sys.argv[3:separator]
members_to_restrict = sys.argv[separator + 1:]
with open(source, encoding="utf-8") as handle:
    policy = json.load(handle)

blocked = set(members_to_remove)
required = set(members_to_restrict)
bindings = []
for binding in policy.get("bindings", []):
    role = binding.get("role")
    members = [
        member
        for member in binding.get("members", [])
        if member not in blocked
        and not (member in required and role != "roles/secretmanager.secretAccessor")
    ]
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

# Remove broad project-level Secret Accessor grants for every principal managed
# here. Developer Connect's separate regional OAuth secret remains untouched.
for MEMBER in "${REQUIRED_ACCESSORS[@]}" "${REMOVE_DIRECT_ACCESS[@]}"; do
  gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="${ACCESSOR_ROLE}" \
    --condition=None \
    --quiet >/dev/null 2>&1 || true
done

for MEMBER in "${REQUIRED_ACCESSORS[@]}"; do
  # Grant access only on the single IronMan token secret.
  gcloud secrets add-iam-policy-binding "${SECRET}" \
    --project="${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="${ACCESSOR_ROLE}" \
    --condition=None \
    --quiet >/dev/null
done

gcloud secrets get-iam-policy "${SECRET}" --project="${PROJECT_ID}" --format=json \
  >"${FINAL_POLICY}"
python3 - "${FINAL_POLICY}" "${REMOVE_DIRECT_ACCESS[@]}" -- "${REQUIRED_ACCESSORS[@]}" <<'PY'
import json
import sys

separator = sys.argv.index("--")
policy_path = sys.argv[1]
blocked = set(sys.argv[2:separator])
required = set(sys.argv[separator + 1:])
with open(policy_path, encoding="utf-8") as handle:
    policy = json.load(handle)

roles_by_member = {}
for binding in policy.get("bindings", []):
    for member in binding.get("members", []):
        roles_by_member.setdefault(member, set()).add(binding.get("role"))

if any(member in roles_by_member for member in blocked):
    raise SystemExit("Unrelated principal still has direct access to the IronMan secret.")

expected = {"roles/secretmanager.secretAccessor"}
for member in required:
    if roles_by_member.get(member) != expected:
        raise SystemExit(f"Unexpected direct secret roles for {member}.")
PY

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

# Version 4 is now proven live. Disable only the three known superseded tokens;
# disabling is recoverable and no secret value is read or printed here.
for VERSION in "${STALE_SECRET_VERSIONS[@]}"; do
  STATE="$(gcloud secrets versions describe "${VERSION}" \
    --project="${PROJECT_ID}" --secret="${SECRET}" --format='value(state)')"
  if [[ "${STATE}" == "ENABLED" ]]; then
    gcloud secrets versions disable "${VERSION}" \
      --project="${PROJECT_ID}" --secret="${SECRET}" --quiet >/dev/null
  fi
done

echo "IronMan IAM hardening complete."
echo "Authorized request: HTTP ${AUTH_STATUS}; unauthorized request: HTTP ${UNAUTH_STATUS}."
echo "Cloud Run is pinned to ${SECRET}:${SECRET_VERSION}."
echo "Superseded secret versions 1-3 are disabled; version 4 remains enabled."
echo "IAM backup: ${BACKUP_POLICY}"
