#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Keep dependency setup deterministic and non-interactive after task merges.
uv sync --frozen --no-install-project
yarn --cwd frontend install --frozen-lockfile --non-interactive

# Rebuild and exercise both sides of the app so a bad merge fails early.
yarn --cwd frontend build
pytest -q backend/tests