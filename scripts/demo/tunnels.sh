#!/usr/bin/env bash
# Expose the web app and the open-pool miner over HTTPS with Cloudflare quick tunnels, then print
# the phone URL and a QR code. Phones need HTTPS for tilt sensors, and an HTTPS page cannot call an
# HTTP miner, so both ends get a tunnel. This publishes local services to the internet, so run it
# yourself and stop it when the demo is over.
#
# Usage: scripts/demo/tunnels.sh [WEB_PORT] [MINER_PORT]
# Start `npm run preview` in web/ and the miner (with MINER_TRUST_PROXY=1) first.
set -euo pipefail

WEB_PORT=${1:-4173}
MINER_PORT=${2:-8091}
LOG_DIR=${TUNNEL_LOG_DIR:-/tmp}

start_tunnel() {
  local port=$1 log=$2
  cloudflared tunnel url "http://localhost:${port}" >"$log" 2>&1 &
  echo $! >"$log.pid"
  for _ in $(seq 1 40); do
    url=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$log" | head -1 || true)
    if [ -n "$url" ]; then echo "$url"; return 0; fi
    sleep 1
  done
  echo "tunnel for port $port did not start, see $log" >&2
  return 1
}

WEB_URL=$(start_tunnel "$WEB_PORT" "$LOG_DIR/tunnel-web.log")
MINER_URL=$(start_tunnel "$MINER_PORT" "$LOG_DIR/tunnel-miner.log")
PHONE_URL="${WEB_URL}/?pool=${MINER_URL}"

echo "web:   $WEB_URL"
echo "miner: $MINER_URL"
echo "phone: $PHONE_URL"
uv run --with qrcode python -c "import qrcode,sys; q=qrcode.QRCode(border=1); q.add_data(sys.argv[1]); q.print_ascii(invert=True)" "$PHONE_URL"
echo "Stop the tunnels with: kill \$(cat $LOG_DIR/tunnel-web.log.pid $LOG_DIR/tunnel-miner.log.pid)"
