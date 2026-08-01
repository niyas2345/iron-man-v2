# WebSocket voice streaming and Cloud Run setup

This file documents how to configure the Cloud Run environment and secrets to
run the Google Cloud Speech streaming adapter in production.

1) Build & deploy (example):

   gcloud builds submit --tag gcr.io/PROJECT_ID/iron-man-v2:latest
   gcloud run deploy iron-man-v2 --image gcr.io/PROJECT_ID/iron-man-v2:latest --region=us-central1 --platform=managed --allow-unauthenticated

2) Cloud Run environment variables & secrets

   Recommended (using Secret Manager):

   # Create a secret containing the service account JSON
   gcloud secrets create google-speech-creds --data-file=service-account.json --project=PROJECT_ID

   # Grant Cloud Run service account access to read the secret (if different)
   gcloud secrets add-iam-policy-binding google-speech-creds --member=serviceAccount:SERVICE_ACCOUNT_EMAIL --role=roles/secretmanager.secretAccessor --project=PROJECT_ID

   # When deploying Cloud Run, mount the secret as an environment variable
   gcloud run deploy iron-man-v2 \
     --image gcr.io/PROJECT_ID/iron-man-v2:latest \
     --update-env-vars=GOOGLE_SPEECH_CREDENTIALS_JSON="$(gcloud secrets versions access latest --secret=google-speech-creds)" \
     --region=us-central1 --platform=managed

   Alternatively set GOOGLE_APPLICATION_CREDENTIALS to the path inside the container
   where you mount a filesystem secret with the JSON file.

3) Runtime expectations

   - The streaming WebSocket endpoint is at: ws://<host>/api/voice/stream
   - The transcript-first fallback remains at /api/voice (unchanged).
   - If neither GOOGLE_APPLICATION_CREDENTIALS nor GOOGLE_SPEECH_CREDENTIALS_JSON is
     present, the WebSocket endpoint will return a JSON error message
     {"error":"missing_google_credentials", "detail": "..."} and close.

4) Port / Docker

   The Dockerfile and Cloud Run both use PORT=8080 by default. The FastAPI
   startup command uses that environment variable so no changes are required.
