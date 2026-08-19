#!/bin/bash
# deploy.sh — Deploy Job-Pilot AI to Google Cloud Run + Firebase Hosting
# Prerequisites: gcloud CLI installed, firebase CLI installed
# Usage: ./deploy.sh

set -e

# ── CONFIG ────────────────────────────────────────────────────────────────────
PROJECT_ID="your-gcp-project-id"          # <- Change this
REGION="asia-south1"                       # Mumbai — closest to India
API_IMAGE="gcr.io/$PROJECT_ID/jobpilot-backend"
WORKER_IMAGE="gcr.io/$PROJECT_ID/jobpilot-worker"

# ── Set active project ────────────────────────────────────────────────────────
echo "→ Setting GCP project: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# ── Build & push backend Docker image ────────────────────────────────────────
echo "→ Building backend Docker image..."
cd backend
gcloud builds submit --tag $API_IMAGE .
cd ..

# ── Deploy FastAPI to Cloud Run ───────────────────────────────────────────────
echo "→ Deploying FastAPI backend to Cloud Run..."
gcloud run deploy jobpilot-backend \
  --image $API_IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 3 \
  --min-instances 0 \
  --command "uvicorn,app.main:app,--host,0.0.0.0,--port,8000" \
  --set-env-vars="APP_ENV=production" \
  --set-secrets="\
GOOGLE_API_KEY=jobpilot-gemini-key:latest,\
DATABASE_URL=jobpilot-db-url:latest,\
REDIS_URL=jobpilot-redis-url:latest,\
CELERY_BROKER_URL=jobpilot-celery-broker:latest,\
JWT_PRIVATE_KEY=jobpilot-jwt-private:latest,\
JWT_PUBLIC_KEY=jobpilot-jwt-public:latest"

# ── Get the API URL ───────────────────────────────────────────────────────────
API_URL=$(gcloud run services describe jobpilot-backend \
  --region $REGION \
  --format 'value(status.url)')
echo "✅ API deployed at: $API_URL"

# ── Deploy Celery Worker to Cloud Run (always-on) ────────────────────────────
echo "→ Deploying Celery worker..."
gcloud run deploy jobpilot-worker \
  --image $API_IMAGE \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 2 \
  --command "celery,-A,app.tasks.celery_app,worker,--loglevel=info,--concurrency=2" \
  --set-env-vars="APP_ENV=production" \
  --set-secrets="\
GOOGLE_API_KEY=jobpilot-gemini-key:latest,\
DATABASE_URL=jobpilot-db-url:latest,\
REDIS_URL=jobpilot-redis-url:latest,\
CELERY_BROKER_URL=jobpilot-celery-broker:latest,\
JWT_PRIVATE_KEY=jobpilot-jwt-private:latest,\
JWT_PUBLIC_KEY=jobpilot-jwt-public:latest"

# ── Run Alembic migrations ────────────────────────────────────────────────────
echo "→ Running database migrations on Supabase..."
cd backend
DATABASE_URL_SYNC=$(echo $DATABASE_URL | sed 's/asyncpg/psycopg2/')
docker run --rm -e DATABASE_URL="$DATABASE_URL_SYNC" $API_IMAGE \
  alembic upgrade head || echo "⚠️  Run migrations manually if Docker not available locally"
cd ..

# ── Build Flutter web ─────────────────────────────────────────────────────────
echo "→ Building Flutter web app..."
cd frontend
flutter build web --release \
  --dart-define=API_URL="$API_URL/api/v1" \
  --dart-define=WS_URL="$(echo $API_URL | sed 's/https/wss/')/api/v1" \
  --web-renderer canvaskit
cd ..

# ── Deploy to Firebase Hosting ────────────────────────────────────────────────
echo "→ Deploying Flutter web to Firebase Hosting..."
firebase deploy --only hosting

echo ""
echo "🚀 Deployment complete!"
echo "   Frontend: https://$PROJECT_ID.web.app"
echo "   API:      $API_URL/api/docs"
