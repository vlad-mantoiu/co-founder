#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# Backend currently requires ANTHROPIC_API_KEY at startup (pydantic settings).
# For local UI/dev you can set a real key; otherwise we provide a dummy to allow boot.
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "⚠️  ANTHROPIC_API_KEY is not set. Using a dummy value so the backend can start."
  echo "    (Set ANTHROPIC_API_KEY=<real key> to use agent features.)"
  export ANTHROPIC_API_KEY=dummy
fi

pids=()
cleanup() {
  echo "\nStopping dev servers..."
  for pid in "${pids[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

echo "==> Starting backend on http://127.0.0.1:${BACKEND_PORT}"
(
  cd "$ROOT_DIR/backend"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  uvicorn app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT"
) &
pids+=("$!")

echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --port "$FRONTEND_PORT"
) &
pids+=("$!")

echo "\n✅ Dev servers running"
echo "- Frontend: http://localhost:${FRONTEND_PORT}"
echo "- Backend:  http://127.0.0.1:${BACKEND_PORT}/api/health"

echo "\nPress Ctrl+C to stop."
wait
