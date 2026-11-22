#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
echo "Grab & Go running at http://127.0.0.1:8000"
exec python -m uvicorn app:app --host "${GRAB_GO_HOST:-127.0.0.1}" --port "${GRAB_GO_PORT:-8000}"
