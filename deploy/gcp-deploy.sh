#!/usr/bin/env bash
# Deploy CourseCompass API + Next.js frontend to Cloud Run (Artifact Registry + Cloud Build).
#
# Prerequisites:
#   gcloud auth login && gcloud config set project YOUR_PROJECT_ID
#   gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com
# Grant the Cloud Run runtime service account Vertex AI User (roles/aiplatform.user), e.g.:
#   PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')
#   gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
#     --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
#     --role="roles/aiplatform.user"
#
# Usage:
#   export GCP_PROJECT=your-project-id
#   export GCP_REGION=us-central1          # optional
#   export LLM_MODEL=vertex_ai/gemini-2.5-flash   # optional
#   export PLANS_TO_GENERATE=plan_a,plan_b,plan_c   # optional (default in script)
#   ./deploy/gcp-deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${GCP_PROJECT:?Set GCP_PROJECT to your Google Cloud project id}"
GCP_REGION="${GCP_REGION:-us-central1}"
LLM_MODEL="${LLM_MODEL:-vertex_ai/gemini-2.5-flash}"
VERTEX_LOCATION="${VERTEX_LOCATION:-$GCP_REGION}"
# Match PRD §7.5 (A/B/C). Code default is plan_a only; Cloud Run sets all three.
PLANS_TO_GENERATE="${PLANS_TO_GENERATE:-plan_a,plan_b,plan_c}"
API_SERVICE="${API_SERVICE:-coursecompass-api}"
WEB_SERVICE="${WEB_SERVICE:-coursecompass-web}"
AR_REPO="${AR_REPO:-coursecompass}"

IMAGE_BASE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}"
API_IMAGE="${IMAGE_BASE}/api:$(date +%Y%m%d-%H%M%S)"
WEB_IMAGE="${IMAGE_BASE}/web:$(date +%Y%m%d-%H%M%S)"

echo "==> Ensuring Artifact Registry repo: ${AR_REPO} (${GCP_REGION})"
if ! gcloud artifacts repositories describe "${AR_REPO}" --location="${GCP_REGION}" &>/dev/null; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${GCP_REGION}" \
    --description="CourseCompass images"
fi

echo "==> Cloud Build: API image -> ${API_IMAGE}"
gcloud builds submit --config=deploy/cloudbuild-api.yaml \
  --substitutions=_IMAGE="${API_IMAGE}" \
  --project="${GCP_PROJECT}" \
  .

# Use ^@^ so PLANS_TO_GENERATE can contain commas (gcloud treats comma as pair sep by default).
API_ENV_VARS="^@^LLM_MODEL=${LLM_MODEL}@CHROMA_PATH=/app/chroma_db@GOOGLE_CLOUD_PROJECT=${GCP_PROJECT}@VERTEXAI_LOCATION=${VERTEX_LOCATION}@PLANS_TO_GENERATE=${PLANS_TO_GENERATE}"

API_DEPLOY_FLAGS=(
  --image="${API_IMAGE}"
  --region="${GCP_REGION}"
  --project="${GCP_PROJECT}"
  --allow-unauthenticated
  --memory=2Gi
  --cpu=2
  --timeout=900
  --set-env-vars="${API_ENV_VARS}"
)
if [[ -n "${CLOUD_RUN_SERVICE_ACCOUNT:-}" ]]; then
  API_DEPLOY_FLAGS+=(--service-account="${CLOUD_RUN_SERVICE_ACCOUNT}")
fi

echo "==> Deploy API: ${API_SERVICE}"
gcloud run deploy "${API_SERVICE}" "${API_DEPLOY_FLAGS[@]}"

API_URL="$(gcloud run services describe "${API_SERVICE}" --region="${GCP_REGION}" --project="${GCP_PROJECT}" --format='value(status.url)')"
echo "API URL: ${API_URL}"

echo "==> Cloud Build: Web image (NEXT_PUBLIC_API_BASE=${API_URL})"
gcloud builds submit --config=deploy/cloudbuild-web.yaml \
  --substitutions=_IMAGE="${WEB_IMAGE}",_API_URL="${API_URL}" \
  --project="${GCP_PROJECT}" \
  .

echo "==> Deploy Web: ${WEB_SERVICE}"
gcloud run deploy "${WEB_SERVICE}" \
  --image="${WEB_IMAGE}" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT}" \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1

WEB_URL="$(gcloud run services describe "${WEB_SERVICE}" --region="${GCP_REGION}" --project="${GCP_PROJECT}" --format='value(status.url)')"
echo ""
echo "Done."
echo "  API: ${API_URL}"
echo "  App: ${WEB_URL}"
echo ""
echo "If Vertex calls fail, ensure the Cloud Run service account has roles/aiplatform.user on this project."
