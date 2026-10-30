# Localnet Setup and Testing Guide

All commands run from the repository root (`/Users/jovian/Developer/bittesnor`) unless noted.

## Prerequisites

- Docker Desktop running (supports Apple Silicon `arm64`)
- Python 3.12 with `uv`
- Node 20 or newer with `npm`

---

## 1. Environment Configuration (`.env`)

Ensure a `.env` file exists in the repository root with a valid 32-byte Fernet key for encrypting custodial player wallets:

```bash
python3 -c "from cryptography.fernet import Fernet; print('WALLET_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" > .env
```

If `.env` already exists, keep your existing `WALLET_ENCRYPTION_KEY` so stored wallets in `data/hosted/accounts.db` remain decryptable.

---

## 2. Start the Subtensor Localnet in Docker

Start the fast-block Subtensor node container on `ws://127.0.0.1:9944`:

```bash
scripts/localnet/up.sh
```

Verify the chain is producing blocks:

```bash
uv run --python 3.12 python -c "import bittensor as bt; print('block:', bt.Subtensor('ws://127.0.0.1:9944').block)"
```

---

## 3. Create and Tune the Subnet (Run Once per Fresh Chain)

Fund `bittesnor-owner` and `bittesnor-validator` from the local `//Alice` dev account, register the subnet (`netuid 2` on a fresh chain), start emissions, register the validator, and add stake:

```bash
uv run --python 3.12 python scripts/localnet/setup.py
```

Disable commit-reveal weights and set the weights rate limit to `0` on `netuid 2`:

```bash
uv run --python 3.12 python scripts/localnet/tune.py 2
```

---

## 4. Start the Hosted Miner and Validator

Run both the multi-player hosted miner (`http://127.0.0.1:8091`) and the validator worker against `netuid 2`:

```bash
NETUID=2 scripts/localnet/run_all.sh
```

Logs are written to:

- `data/logs/miner.log` (HTTP requests and background `registrar` thread)
- `data/logs/validator.log` (trajectory pulls, MuJoCo replay verdicts, `set_weights`, and epoch Merkle root commitments)

Tail the logs in another terminal:

```bash
tail -f data/logs/miner.log data/logs/validator.log
```

Check the miner health endpoint:

```bash
curl -s http://127.0.0.1:8091/health
```

---

## 5. Start the Web Application

In a separate terminal, start the Vite dev server on `http://localhost:5173`:

```bash
cd web
npm install
npm run dev
```

Pages:

- Landing page: `http://localhost:5173/`
- Teleop simulator (play and submit): `http://localhost:5173/play.html`
- Live network, leaderboard, validator weights, and epoch roots: `http://localhost:5173/network.html`

---

## 6. Test Miner Registration, Trajectory Submission, and Scoring

### Option A: Simulated Miner via CLI (`sim_phone.py`)

Simulate one or more players. Each distinct name gets a new custodial wallet, receives TAO from the `//Alice` treasury, registers on-chain as a new UID on `netuid 2`, fetches a task ticket, solves the task in MuJoCo, submits the trajectory, and waits for the validator verdict:

```bash
# Single miner named miner-alpha-0
uv run --python 3.12 python scripts/dev/sim_phone.py http://127.0.0.1:8091 1 1 miner-alpha

# 3 concurrent miners (batch-0, batch-1, batch-2)
uv run --python 3.12 python scripts/dev/sim_phone.py http://127.0.0.1:8091 3 3 batch
```

### Option B: Manual API Calls with Dev Login (`AUTH_DEV_LOGIN=1`)

1. Create/inspect a player account and trigger background on-chain registration:

```bash
curl -s -H "Authorization: Bearer dev:player1" http://127.0.0.1:8091/me | python3 -m json.tool
```

2. Fetch a task ticket (`rack_vial` or `put_cube_in_bowl`):

```bash
curl -s -H "Authorization: Bearer dev:player1" "http://127.0.0.1:8091/ticket?task=put_cube_in_bowl" | python3 -m json.tool
```

3. Inspect live network state (miners, UIDs, scores, incentives, emissions, validators, and recent verdicts):

```bash
curl -s http://127.0.0.1:8091/network | python3 -m json.tool
```

4. Inspect the leaderboard:

```bash
curl -s http://127.0.0.1:8091/leaderboard | python3 -m json.tool
```

---

## 7. Export Accepted Runs to a LeRobot Dataset

Export all validator-accepted episodes from `data/accepted` into a LeRobot v0.6.1 dataset:

```bash
uv run --python 3.12 --extra export python -m export.lerobot_export data/accepted out/sample bittesnor/teleop-so101-sim-sample
```

---

## 8. Resetting Everything for a Clean Run

To wipe the local chain and all local miner/validator databases and start fresh:

```bash
pkill -f "miner.main|validator.main|run_all.sh" || true
docker rm -f bittesnor-localnet
rm -rf data/hosted data/accepted data/validator.db data/logs

scripts/localnet/up.sh
uv run --python 3.12 python scripts/localnet/setup.py
uv run --python 3.12 python scripts/localnet/tune.py 2
NETUID=2 scripts/localnet/run_all.sh
```
