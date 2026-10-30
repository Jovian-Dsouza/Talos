#!/usr/bin/env bash
# Run the hosted miner and the validator against the local chain. Ctrl-C stops both.
# Needs: scripts/localnet/up.sh and setup.py done, and NETUID set (setup.py prints it).
set -euo pipefail
cd "$(dirname "$0")/../.."

set -a
[ -f .env ] && . ./.env
set +a
: "${NETUID:?set NETUID to the subnet setup.py created}"
MINER_PORT="${MINER_PORT:-8091}"
export NETUID MINER_PORT AUTH_DEV_LOGIN="${AUTH_DEV_LOGIN:-1}" CHAIN_ENDPOINT="${CHAIN_ENDPOINT:-ws://127.0.0.1:9944}"
export HOSTED_MINER_URL="http://127.0.0.1:${MINER_PORT}" POLL_SECONDS="${POLL_SECONDS:-2}"
export MINER_VALIDATOR_ALLOWLIST="$(uv run --python 3.12 python -c "import bittensor as bt; print(bt.Wallet(name='${VALIDATOR_WALLET:-taunet-validator}', hotkey='default').hotkey.ss58_address)")"

mkdir -p data/logs
uv run --python 3.12 python -m miner.main >data/logs/miner.log 2>&1 &
miner=$!
uv run --python 3.12 python -m validator.main >data/logs/validator.log 2>&1 &
validator=$!
trap 'kill $miner $validator 2>/dev/null || true' EXIT INT TERM
echo "miner pid $miner on :$MINER_PORT, validator pid $validator. Logs in data/logs/"
wait
