#!/usr/bin/env bash
# Run the practice backend + browser MuJoCo teleop app. Stop with Ctrl+C.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

for port in 8091 5173; do
  if lsof -ti:"$port" >/dev/null 2>&1; then
    echo "Port $port already in use; stop that process first or: lsof -ti:$port | xargs kill"
    exit 1
  fi
done

cleanup() {
  jobs -p | xargs kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Practice API: http://127.0.0.1:8091"
echo "Simulator:    http://localhost:5173/"
echo "Press Ctrl+C to stop both."
echo

uv run --python 3.12 python scripts/dev/practice.py &
npm run dev --prefix web &
wait
