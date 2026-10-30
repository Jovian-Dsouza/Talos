#!/usr/bin/env bash
# Expose the local chain RPC (default port 9944) to the hosted backend with a Cloudflare quick tunnel and
# print the wss URL to use as CHAIN_ENDPOINT on Render. The URL changes every time cloudflared restarts,
# so update CHAIN_ENDPOINT on both Render services after a restart. This publishes the local chain to the
# internet, so run it yourself and stop it when you are done.
#
# Usage: scripts/demo/chain_tunnel.sh [CHAIN_PORT]
set -euo pipefail

PORT=${1:-9944}
LOG=${TUNNEL_LOG_DIR:-/tmp}/tunnel-chain.log

cloudflared tunnel --url "http://127.0.0.1:${PORT}" --no-autoupdate >"$LOG" 2>&1 &
echo $! >"$LOG.pid"
for _ in $(seq 1 40); do
  url=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" | head -1 || true)
  if [ -n "$url" ]; then
    echo "CHAIN_ENDPOINT=wss://${url#https://}"
    echo "Stop the tunnel with: kill \$(cat $LOG.pid)"
    exit 0
  fi
  sleep 1
done
echo "tunnel did not start, see $LOG" >&2
exit 1
