#!/usr/bin/env bash
set -euo pipefail

api_pid=""
frontend_pid=""

shutdown() {
  for pid in "$api_pid" "$frontend_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait "$api_pid" "$frontend_pid" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

(
  cd backend
  exec env MOCK_DATA=true uvicorn server:app --host 0.0.0.0 --port 5001
) &
api_pid=$!

(
  cd frontend
  exec env HOST=0.0.0.0 PORT=5000 BROWSER=none yarn start
) &
frontend_pid=$!

# If either server stops, end the workflow and clean up the other process.
wait -n "$api_pid" "$frontend_pid"