#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
exec python edge/edge_node.py --source "${1:-sample_videos/shop_shelf.mp4}" --server "${GRAB_GO_SERVER:-http://127.0.0.1:8000}" --node-id "${NODE_ID:-shelf-01}"
