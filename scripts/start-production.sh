#!/usr/bin/env bash
# Production start script.
#
# Builds the React frontend once, then starts FastAPI on port 5000.
# FastAPI serves /api/* through its routers and delivers the static React build
# for all other paths (StaticFiles mount + SPA catch-all in server.py).
# No reverse proxy or second process is required.
set -euo pipefail

echo "Building frontend…"
(cd frontend && yarn build)
echo "Frontend build complete."

cd backend
exec env MOCK_DATA="false" uvicorn server:app --host 0.0.0.0 --port 5000
