#!/usr/bin/env bash
# Run the hosted miner, the validator and the web app against the local chain. Ctrl-C stops all three.
# Needs: scripts/localnet/up.sh and setup.py done (setup.py saves NETUID to data/localnet.env).
# Ports: MINER_PORT (default 8091) and WEB_PORT (default 5173). RUN_WEB=0 skips the web app.
set -euo pipefail
cd "$(dirname "$0")/../.."

set -a
[ -f .env ] && . ./.env
[ -f data/localnet.env ] && . ./data/localnet.env
[ -f web/.env ] && . ./web/.env
set +a
: "${NETUID:?set NETUID to the subnet setup.py created}"
MINER_PORT="${MINER_PORT:-8091}"
WEB_PORT="${WEB_PORT:-5173}"
export NETUID MINER_PORT AUTH_DEV_LOGIN="${AUTH_DEV_LOGIN:-1}" CHAIN_ENDPOINT="${CHAIN_ENDPOINT:-ws://127.0.0.1:9944}"
export HOSTED_MINER_URL="http://127.0.0.1:${MINER_PORT}" POLL_SECONDS="${POLL_SECONDS:-2}"
export MINER_VALIDATOR_ALLOWLIST="$(uv run --python 3.12 python -c "import bittensor as bt; print(bt.Wallet(name='${VALIDATOR_WALLET:-taunet-validator}', hotkey='default').hotkey.ss58_address)")"

# Clerk: the publishable key is base64 of the Frontend API host, which is also the session token issuer.
if [ -z "${CLERK_ISSUER:-}" ] && [ -n "${VITE_CLERK_PUBLISHABLE_KEY:-}" ]; then
  CLERK_ISSUER="https://$(python3 -c 'import base64, sys; k = sys.argv[1].split("_", 2)[2]; print(base64.b64decode(k + "=" * (-len(k) % 4)).decode().rstrip("$"))' "$VITE_CLERK_PUBLISHABLE_KEY")"
  export CLERK_ISSUER
fi
if [ -n "${CLERK_ALLOWED_ORIGINS:-}" ]; then
  export CLERK_ALLOWED_ORIGINS="${CLERK_ALLOWED_ORIGINS},http://localhost:${WEB_PORT}"
fi
[ -n "${CLERK_ISSUER:-}" ] || echo "warning: no CLERK_ISSUER or VITE_CLERK_PUBLISHABLE_KEY, Google sign-in will be refused (dev login only)"
[ -n "${CLERK_SECRET_KEY:-}" ] || echo "warning: CLERK_SECRET_KEY is not set, first Google sign-in cannot load the player's profile"

mkdir -p data/logs
uv run --python 3.12 python -m miner.main >data/logs/miner.log 2>&1 &
pids=($!)
uv run --python 3.12 python -m validator.main >data/logs/validator.log 2>&1 &
pids+=($!)
if [ "${RUN_WEB:-1}" = "1" ]; then
  (cd web && POOL_TARGET="http://127.0.0.1:${MINER_PORT}" VITE_ALLOW_DEV_LOGIN="${VITE_ALLOW_DEV_LOGIN:-$AUTH_DEV_LOGIN}" \
    exec ./node_modules/.bin/vite --host --port "$WEB_PORT" --strictPort) >data/logs/web.log 2>&1 &
  pids+=($!)
fi
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT INT TERM
echo "miner on :$MINER_PORT, validator, web on :$WEB_PORT (pids ${pids[*]}). Clerk issuer: ${CLERK_ISSUER:-none}. Logs in data/logs/"
wait
