#!/usr/bin/env bash
set -euo pipefail

# One-time Google Cloud setup for the GitHub Actions deployment workflow.
# This script creates no long-lived service-account key and prints no secret values.

PROJECT_ID="project-2228bebf-326d-4183-a0d"
PROJECT_NUMBER="761020604913"
REGION="me-central1"
GITHUB_REPOSITORY="niyas2345/iron-man-v2"
POOL_ID="github"
PROVIDER_ID="ironman-recovery"
DEPLOYER_ID="github-ironman-deployer"
RUNTIME_SERVICE_ACCOUNT="ironman-core-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
TOKEN_SECRET="ironman-api-token"

DEPLOYER_SERVICE_ACCOUNT="${DEPLOYER_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
COMPUTE_SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Checking Google Cloud account and project..."
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "No active Google Cloud account was found. Reopen Cloud Shell and authorize it." >&2
  exit 1
fi

ACTUAL_PROJECT_NUMBER="$(
  gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)'
)"
if [[ "${ACTUAL_PROJECT_NUMBER}" != "${PROJECT_NUMBER}" ]]; then
  echo "Project identity check failed; refusing to modify a different project." >&2
  exit 1
fi

gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud config set run/region "${REGION}" >/dev/null

echo "Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  iamcredentials.googleapis.com \
  secretmanager.googleapis.com \
  sts.googleapis.com \
  aiplatform.googleapis.com \
  --project="${PROJECT_ID}" \
  --quiet

echo "Creating the keyless GitHub deployment service account..."
if ! gcloud iam service-accounts describe "${DEPLOYER_SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${DEPLOYER_ID}" \
    --project="${PROJECT_ID}" \
    --display-name="GitHub IronMan Recovery deployer" \
    --quiet
fi

for ROLE in \
  roles/run.admin \
  roles/run.sourceDeveloper \
  roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEPLOYER_SERVICE_ACCOUNT}" \
    --role="${ROLE}" \
    --condition=None \
    --quiet >/dev/null
done

gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOYER_SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser" \
  --condition=None \
  --quiet >/dev/null

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet >/dev/null

if gcloud iam service-accounts describe "${COMPUTE_SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${COMPUTE_SERVICE_ACCOUNT}" \
    --role="roles/run.builder" \
    --condition=None \
    --quiet >/dev/null

  gcloud iam service-accounts add-iam-policy-binding "${COMPUTE_SERVICE_ACCOUNT}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${DEPLOYER_SERVICE_ACCOUNT}" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None \
    --quiet >/dev/null
else
  echo "Compute default service account is not ready yet." >&2
  echo "Wait one minute, then run this script again." >&2
  exit 1
fi

echo "Checking the existing Iron Man bearer-token secret..."
if ! gcloud secrets describe "${TOKEN_SECRET}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  GENERATED_TOKEN="$(openssl rand -hex 32)"
  printf '%s' "${GENERATED_TOKEN}" | gcloud secrets create "${TOKEN_SECRET}" \
    --project="${PROJECT_ID}" \
    --replication-policy="automatic" \
    --data-file=- \
    --quiet
  unset GENERATED_TOKEN
  echo "Created ${TOKEN_SECRET}. Its value was not printed."
fi

for MEMBER in \
  "serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
  "serviceAccount:${DEPLOYER_SERVICE_ACCOUNT}"; do
  gcloud secrets add-iam-policy-binding "${TOKEN_SECRET}" \
    --project="${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet >/dev/null
done

echo "Creating the GitHub Workload Identity pool..."
if ! gcloud iam workload-identity-pools describe "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions" \
    --quiet
fi

PROVIDER_ARGUMENTS=(
  --project="${PROJECT_ID}"
  --location="global"
  --workload-identity-pool="${POOL_ID}"
  --display-name="IronMan Recovery"
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner"
  --attribute-condition="assertion.repository == '${GITHUB_REPOSITORY}'"
  --issuer-uri="https://token.actions.githubusercontent.com"
  --quiet
)

if gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers update-oidc "${PROVIDER_ID}" \
    "${PROVIDER_ARGUMENTS[@]}"
else
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    "${PROVIDER_ARGUMENTS[@]}"
fi

POOL_NAME="$(
  gcloud iam workload-identity-pools describe "${POOL_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --format='value(name)'
)"
REPOSITORY_PRINCIPAL="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPOSITORY}"

gcloud iam service-accounts add-iam-policy-binding "${DEPLOYER_SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --member="${REPOSITORY_PRINCIPAL}" \
  --role="roles/iam.workloadIdentityUser" \
  --condition=None \
  --quiet >/dev/null

echo
echo "Google Cloud setup complete for ${GITHUB_REPOSITORY}."
echo "No service-account key was created and no secret value was printed."
echo "Vertex AI Gemini Live uses the runtime service account; no API key is required."
echo "Wait five minutes for IAM propagation before deploying."
