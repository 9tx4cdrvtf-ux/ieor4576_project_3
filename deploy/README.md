# Deploy CourseCompass to Google Cloud Run

This deploys **two services**: FastAPI (`coursecompass-api`) and Next.js (`coursecompass-web`). Images are built with **Cloud Build** and stored in **Artifact Registry**. The `chroma_db/` directory is baked into the API image.

## Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk) installed and authenticated: `gcloud auth login`.
2. Billing enabled on the project.
3. Enable APIs:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com
```

4. **Vertex AI**: Grant the **Cloud Run runtime** service account the role `roles/aiplatform.user` on the project (default is the Compute Engine default service account):

```bash
export GCP_PROJECT=YOUR_PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

To use a **custom** runtime service account instead, create one, grant it `roles/aiplatform.user`, then set `CLOUD_RUN_SERVICE_ACCOUNT` before running the script (see `gcp-deploy.sh` header).

## One-command deploy

From the **repository root**:

```bash
export GCP_PROJECT=YOUR_PROJECT_ID
export GCP_REGION=us-central1          # optional
export LLM_MODEL=vertex_ai/gemini-2.5-flash   # optional
./deploy/gcp-deploy.sh
```

The script will:

1. Create an Artifact Registry repository `coursecompass` if missing.
2. Build and push the API image, deploy `coursecompass-api`.
3. Build the web image with `NEXT_PUBLIC_API_BASE` set to the API URL, deploy `coursecompass-web`.

Open the printed **App** URL in a browser.

## Local Docker (optional)

From repo root, with Docker installed:

```bash
docker build -f docker/Dockerfile.api -t coursecompass-api .
docker run --rm -p 8080:8080 -e PORT=8080 coursecompass-api
```

Frontend (replace API URL if needed):

```bash
docker build -f docker/Dockerfile.web --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8080 -t coursecompass-web .
docker run --rm -p 3000:8080 -e PORT=8080 coursecompass-web
```

On Apple Silicon, add `--platform linux/amd64` to `docker build` if you push images to Cloud Run and hit architecture issues.

## Redeploy after API URL change

If you only change the backend URL, rebuild the **web** image so `NEXT_PUBLIC_API_BASE` matches; re-run the full script, or run the web `cloudbuild-web` step manually with the correct `_API_URL`.
