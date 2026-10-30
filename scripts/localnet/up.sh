#!/usr/bin/env bash
# Start a fast-block Subtensor localnet in Docker (arm64 supported) and wait for RPC.
set -euo pipefail

NAME=taunet-localnet
IMAGE=${LOCALNET_IMAGE:-ghcr.io/opentensor/subtensor-localnet:latest}

if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  docker start "$NAME" >/dev/null
else
  docker run -d --name "$NAME" -p 9944:9944 -p 9945:9945 "$IMAGE" >/dev/null
fi

for _ in $(seq 1 60); do
  if curl -s -o /dev/null -X POST -H 'Content-Type: application/json' \
    -d '{"id":1,"jsonrpc":"2.0","method":"system_health","params":[]}' http://127.0.0.1:9944; then
    echo "localnet up at ws://127.0.0.1:9944"
    exit 0
  fi
  sleep 2
done
echo "localnet did not come up" >&2
exit 1
