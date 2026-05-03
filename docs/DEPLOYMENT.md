# Deployment

How to take Sankalp from a fresh `git clone` to a live Cloud Run URL. Written for a solo developer with `gcloud` and `pnpm` already installed.

---

## 1. What you'll deploy

Two Cloud Run services in `asia-south1`:

| Service | Image | Min instances | Max instances | Memory | Concurrency |
|---|---|---|---|---|---|
| `sankalp-backend` | Python FastAPI + ADK | 1 (during demo) | 5 | 1 GiB | 20 |
| `sankalp-frontend` | Next.js standalone | 0 | 5 | 512 MiB | 80 |

Plus:

- Firestore (Native mode) in `asia-south1`
- Cloud Storage bucket `sankalp-assets-{project_id}` in `asia-south1`
- Three secrets in Secret Manager
- Cloud Run service account with Firestore, Storage, Vision, Maps API access

Total cost during the judging window (estimate): **under $2/day** at min-instances=1.

## 2. One-time GCP setup

### 2.1 Project

```bash
export PROJECT_ID=sankalp-prod
export REGION=asia-south1

gcloud projects create $PROJECT_ID --name=Sankalp
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
gcloud config set artifacts/location $REGION

# Link billing — required for Vertex AI, Maps, etc.
gcloud beta billing projects link $PROJECT_ID \
  --billing-account=YOUR_BILLING_ACCOUNT
```

### 2.2 Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  vision.googleapis.com \
  texttospeech.googleapis.com \
  maps-backend.googleapis.com \
  geocoding-backend.googleapis.com \
  directions-backend.googleapis.com \
  places-backend.googleapis.com
```

### 2.3 Firestore

```bash
gcloud firestore databases create \
  --location=$REGION \
  --type=firestore-native
```

Then create the collection-level TTL policy via the Console (CLI doesn't support TTL config directly):

1. Firestore Console → TTL policies → Create policy
2. Collection group: `sessions`
3. Field: `expires_at`

This auto-deletes session documents 24 hours after their `expires_at` timestamp.

### 2.4 Cloud Storage

```bash
export BUCKET=sankalp-assets-$PROJECT_ID
gcloud storage buckets create gs://$BUCKET \
  --location=$REGION \
  --uniform-bucket-level-access

# Public read on /story/* prefix only — for shareable story permalinks
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=allUsers \
  --role=roles/storage.objectViewer \
  --condition='expression=resource.name.startsWith("projects/_/buckets/'$BUCKET'/objects/story/"),title=public_stories,description=Story permalinks are public'
```

### 2.5 Service account

```bash
export SA=sankalp-runtime
gcloud iam service-accounts create $SA --display-name="Sankalp Runtime"

export SA_EMAIL=$SA@$PROJECT_ID.iam.gserviceaccount.com

for ROLE in \
  roles/datastore.user \
  roles/storage.objectAdmin \
  roles/aiplatform.user \
  roles/secretmanager.secretAccessor \
  roles/logging.logWriter \
  roles/monitoring.metricWriter
do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SA_EMAIL --role=$ROLE
done
```

### 2.6 Secrets

Three secrets. Create each, then store the value.

```bash
# Gemini API key (or use Vertex AI in-project — see §2.7)
gcloud secrets create GOOGLE_API_KEY --replication-policy=automatic
echo -n "your-gemini-key" | gcloud secrets versions add GOOGLE_API_KEY --data-file=-

# Maps Platform key (separate from Gemini key)
gcloud secrets create GOOGLE_MAPS_API_KEY --replication-policy=automatic
echo -n "your-maps-key" | gcloud secrets versions add GOOGLE_MAPS_API_KEY --data-file=-

# Imagen / Vertex AI scoped key (if separate)
gcloud secrets create VERTEX_AI_KEY --replication-policy=automatic
echo -n "your-vertex-key" | gcloud secrets versions add VERTEX_AI_KEY --data-file=-
```

### 2.7 Use Vertex AI in-project (preferred over public Gemini key)

If you'd rather use Vertex AI inside the same project than a Gemini API key:

```bash
# The service account already has aiplatform.user from §2.5
# In code, set GOOGLE_GENAI_USE_VERTEXAI=true and skip GOOGLE_API_KEY
```

`backend/main.py` checks for `GOOGLE_GENAI_USE_VERTEXAI=true` and uses ADC (the service account) instead of the API key. This is cleaner for production but the demo also supports the API-key path.

### 2.8 Maps API key restrictions

In Console → APIs & Services → Credentials → your Maps key:

- **Application restriction:** HTTP referrers, with allowlist:
  - `https://sankalp-frontend-*.run.app/*`
  - `https://sankalp.YOUR_DOMAIN/*` (if custom domain)
  - `http://localhost:3000/*` (dev)
- **API restriction:** restrict to Maps JavaScript, Geocoding, Directions, Places.

The frontend uses this key for the `<Map>` component. The backend uses a *separate* server-side Maps key with no referrer restriction but IP allowlist (Cloud Run's outbound IP range).

## 3. Artifact Registry

```bash
gcloud artifacts repositories create sankalp \
  --repository-format=docker \
  --location=$REGION \
  --description="Sankalp container images"

gcloud auth configure-docker $REGION-docker.pkg.dev
```

## 4. Backend deployment

### 4.1 Dockerfile (backend/Dockerfile)

Already in the repo — the relevant facts:

- Base: `python:3.11-slim`
- Multi-stage to keep final image under 500 MB
- Healthcheck on `/api/healthz` (port 8080) — bare `/healthz` is reserved by GFE on `*.run.app`
- Runs as non-root user `appuser`

### 4.2 Build and push

```bash
cd backend
gcloud builds submit \
  --tag=$REGION-docker.pkg.dev/$PROJECT_ID/sankalp/backend:latest \
  --timeout=20m
```

### 4.3 Deploy

```bash
gcloud run deploy sankalp-backend \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/sankalp/backend:latest \
  --region=$REGION \
  --service-account=$SA_EMAIL \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=5 \
  --concurrency=20 \
  --timeout=300 \
  --port=8080 \
  --allow-unauthenticated \
  --set-env-vars="\
GOOGLE_GENAI_USE_VERTEXAI=true,\
GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
GOOGLE_CLOUD_LOCATION=us-central1,\
FIRESTORE_PROJECT_ID=$PROJECT_ID,\
STORAGE_BUCKET=sankalp-assets-$PROJECT_ID,\
LOG_LEVEL=INFO,\
ENVIRONMENT=production" \
  # Note: GOOGLE_CLOUD_LOCATION drives only the Vertex AI LLM region.
  # The Cloud Run service runs in $REGION (asia-south1). gemini-2.5-pro is
  # not yet provisioned in asia-south1, so LLM calls go to us-central1.
  --set-secrets="\
GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest"
```

### 4.4 Verify

```bash
export BACKEND_URL=$(gcloud run services describe sankalp-backend \
  --region=$REGION --format='value(status.url)')

curl $BACKEND_URL/api/healthz
# Expected: {"status":"ok","service":"sankalp-backend","version":"..."}

bash scripts/smoke_test.sh $BACKEND_URL
# Runs the four-stage SSE smoke test
```

## 5. Frontend deployment

### 5.1 Build env

The frontend is a Next.js 14 app in standalone output mode. It reads two env vars at build time:

```bash
# frontend/.env.production
NEXT_PUBLIC_BACKEND_URL=https://sankalp-backend-XXXXX-as.a.run.app
NEXT_PUBLIC_MAPS_KEY=your-public-maps-key
```

### 5.2 Build and push

```bash
cd frontend
gcloud builds submit \
  --tag=$REGION-docker.pkg.dev/$PROJECT_ID/sankalp/frontend:latest \
  --timeout=20m
```

### 5.3 Deploy

```bash
gcloud run deploy sankalp-frontend \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/sankalp/frontend:latest \
  --region=$REGION \
  --service-account=$SA_EMAIL \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --concurrency=80 \
  --timeout=60 \
  --port=3000 \
  --allow-unauthenticated
```

### 5.4 Verify

```bash
export FRONTEND_URL=$(gcloud run services describe sankalp-frontend \
  --region=$REGION --format='value(status.url)')

echo "Live at: $FRONTEND_URL"
open $FRONTEND_URL  # or xdg-open on Linux
```

## 6. Custom domain (optional)

If you want `sankalp.basuoikantik.in` instead of the `*.run.app` URL:

```bash
gcloud run domain-mappings create \
  --service=sankalp-frontend \
  --domain=sankalp.basuoikantik.in \
  --region=$REGION
```

Add the DNS records gcloud prints at your DNS provider. SSL provisions automatically.

For the hackathon, the `*.run.app` URL is fine — and judges expect it.

## 7. Local development

### 7.1 Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Use the API key path locally for simplicity
export GOOGLE_API_KEY=...
export GOOGLE_MAPS_API_KEY=...
export FIRESTORE_PROJECT_ID=$PROJECT_ID
export STORAGE_BUCKET=sankalp-assets-$PROJECT_ID
# Authenticate ADC for Firestore/Storage/Vision
gcloud auth application-default login

uvicorn main:app --reload --port 8080
```

### 7.2 Frontend

```bash
cd frontend
pnpm install
pnpm dev  # http://localhost:3000
```

The frontend's `.env.local` should point at `http://localhost:8080` for `NEXT_PUBLIC_BACKEND_URL`.

## 8. CI/CD (optional, recommended)

A simple `.github/workflows/deploy.yml` watches `main` and runs:

```
1. backend tests (pytest)
2. frontend type-check + build
3. docker build + push (only if tests pass)
4. cloud run deploy
5. smoke test against the new revision
6. on failure, traffic stays on previous revision (Cloud Run default)
```

Skipping this for hackathon if time-pressed — manual `gcloud run deploy` is fine for three submission attempts.

## 9. Rollback

Cloud Run keeps every revision. To roll back:

```bash
gcloud run services update-traffic sankalp-backend \
  --region=$REGION \
  --to-revisions=sankalp-backend-00012-abc=100
```

Replace the revision name with the prior good one — find via:

```bash
gcloud run revisions list --service=sankalp-backend --region=$REGION
```

## 10. Pre-submission checklist

Before pushing to `main` for the final submission attempt:

- [ ] `pytest backend/tests/ -v` — all green
- [ ] `pnpm --filter frontend type-check` — no errors
- [ ] Repo size: `du -sh --exclude=node_modules --exclude=.next --exclude=.venv .` — under 10 MB
- [ ] Single branch: `git branch -a | grep -v main` returns nothing
- [ ] `.env*` files NOT committed (check `.gitignore`)
- [ ] No API keys in any committed file (`git grep -i "AIza"` returns empty)
- [ ] `README.md` has the live Cloud Run URL filled in
- [ ] `bash scripts/smoke_test.sh $BACKEND_URL` passes
- [ ] Cloud Run min-instances=1 set on backend (cold start safety during judging)
- [ ] Public access allowed on both services (`--allow-unauthenticated`)
- [ ] Repo is public on GitHub
- [ ] Submission form: GitHub URL + Cloud Run URL + vertical = "Election Process Education"

## 11. Costs to expect

For the demo + judging window (about 72 hours):

| Service | Estimated cost |
|---|---|
| Cloud Run (backend, min-1) | $1.50 |
| Cloud Run (frontend, min-0) | $0.10 |
| Firestore | $0.00 (free tier) |
| Cloud Storage | $0.00 (free tier) |
| Vertex AI / Gemini (Flash + Pro) | $1.00 |
| Maps Platform | $0.00 (free tier) |
| Vision API | $0.00 (free tier, 1000 calls) |
| Imagen | $0.50 (limited per session) |
| **Total** | **~$3.10** |

Well within hackathon budget. Set a billing alert at $10 just in case.

## 12. Tear-down (after judging)

```bash
gcloud run services delete sankalp-backend --region=$REGION --quiet
gcloud run services delete sankalp-frontend --region=$REGION --quiet
gcloud storage rm --recursive gs://sankalp-assets-$PROJECT_ID
# Keep the project + Firestore + secrets for v2 work
```
