#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "==> Frontend: lint"
(
  cd "$ROOT_DIR/frontend"
  npm run lint
)

echo "==> Frontend: build"
(
  cd "$ROOT_DIR/frontend"
  npm run build
)

echo "==> Backend: pytest"
(
  cd "$ROOT_DIR/backend"
  if [ ! -d .venv ]; then
    echo "Backend .venv not found; creating..."
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -e ".[dev]" >/dev/null
  pytest
)

echo "✅ All checks passed"
