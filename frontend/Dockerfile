# Frontend Dockerfile for Firebase Hosting build
# Run: docker build -t jobpilot-frontend .
# Then: copy build/web to Firebase

FROM ghcr.io/cirruslabs/flutter:stable AS builder
WORKDIR /app
COPY . .
RUN flutter pub get
ARG API_URL=https://your-api.run.app/api/v1
ARG WS_URL=wss://your-api.run.app/api/v1
RUN flutter build web --release \
    --dart-define=API_URL=$API_URL \
    --dart-define=WS_URL=$WS_URL \
    --web-renderer canvaskit
