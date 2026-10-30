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

For Google sign-in through Clerk, also put `CLERK_SECRET_KEY` in `.env` and `VITE_CLERK_PUBLISHABLE_KEY` in `web/.env` (both gitignored). `run_all.sh` derives `CLERK_ISSUER` from the publishable key when it is not set, and warns at startup if either Clerk value is missing. Dev login (`?dev=NAME` in the page URL, `Bearer dev:NAME` for curl) stays available on localnet for scripted players.

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

Fund `taunet-owner` and `taunet-validator` from the local `//Alice` dev account, register the subnet (`netuid 2` on a fresh chain), start emissions, register the validator, add stake, and publish the subnet's on-chain name, `taunet`. The netuid is saved to `data/localnet.env`, which `run_all.sh` reads:

```bash
uv run --python 3.12 python scripts/localnet/setup.py
```

Set `OWNER_WALLET` or `VALIDATOR_WALLET` to use differently named wallets. Check the name on chain:

```bash
uv run --python 3.12 python -c "import bittensor as bt; print(bt.Subtensor('ws://127.0.0.1:9944').read('subnet_identity', netuid=2))"
```

Disable commit-reveal weights and set the weights rate limit to `0` on `netuid 2` (admin calls refused inside the protected weights window are retried):

```bash
uv run --python 3.12 python scripts/localnet/tune.py 2
```

---

## 4. Start the Hosted Miner, Validator and Web App

One script runs all three against the saved netuid: the multi-player hosted miner (the backend, with Clerk auth), the validator worker, and the Vite web app, which proxies `/pool` to the miner:

```bash
scripts/localnet/run_all.sh
```

Ports default to `MINER_PORT=8091` and `WEB_PORT=5173`. If something else already uses them (for example `scripts/dev/practice.py` or another Vite server), pick others:

```bash
MINER_PORT=8095 WEB_PORT=5174 scripts/localnet/run_all.sh
```

`RUN_WEB=0` skips the web app. Logs are written to:

- `data/logs/miner.log` (HTTP requests, the background `registrar` thread and the stake sampler)
- `data/logs/validator.log` (trajectory pulls, MuJoCo replay verdicts, `set_weights`, and epoch Merkle root commitments)
- `data/logs/web.log` (Vite)

Tail the logs in another terminal:

```bash
tail -f data/logs/miner.log data/logs/validator.log
```

Check the miner health endpoint:

```bash
curl -s http://127.0.0.1:8091/health
```

---

## 5. Use the Web Application

Run `npm install` in `web/` once. Pages (use your `WEB_PORT`):

- Landing page with the live run conveyor: `http://localhost:5173/`
- Play: game lobby (level, XP, daily goal, streak, earnings), the simulator, and the run's journey after submit: `http://localhost:5173/play`
- Live: where every run is, network totals, outcome and time charts, rejection reasons, run feed, miners and validators: `http://localhost:5173/network`
- Datasets: one dataset per task with its latest runs, and an episode browser: `http://localhost:5173/datasets`
- Wallet (signed in): wallet and miner addresses, free TAO, earned TAO, progress and badges: `http://localhost:5173/wallet`

Add `?dev=NAME` to any page to act as a dev player without Google sign-in.

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

5. The data behind the Live, Datasets and Wallet pages:

```bash
curl -s "http://127.0.0.1:8091/activity?window=1h" | python3 -m json.tool   # or window=24h
curl -s http://127.0.0.1:8091/datasets | python3 -m json.tool
curl -s "http://127.0.0.1:8091/episodes?task=put_cube_in_bowl&count=10" | python3 -m json.tool
curl -s -H "Authorization: Bearer dev:player1" http://127.0.0.1:8091/me/progress | python3 -m json.tool
curl -s -H "Authorization: Bearer dev:player1" http://127.0.0.1:8091/me/wallet | python3 -m json.tool
```

On localnet, emissions arrive every tempo (10 fast blocks), so a verified player's earned TAO grows within a minute.

---

## 7. Export Accepted Runs to a LeRobot Dataset

Export all validator-accepted episodes from `data/accepted` into a LeRobot v0.6.1 dataset:

```bash
uv run --python 3.12 --extra export python -m export.lerobot_export data/accepted out/sample taunet/teleop-so101-sim-sample
```

---

## 8. Resetting Everything for a Clean Run

To wipe the local chain and all local miner/validator databases and start fresh:

```bash
pkill -f "scripts/localnet/run_all.sh" || true
docker rm -f taunet-localnet
rm -rf data/hosted data/accepted data/validator.db data/logs data/localnet.env

scripts/localnet/up.sh
uv run --python 3.12 python scripts/localnet/setup.py
uv run --python 3.12 python scripts/localnet/tune.py 2
scripts/localnet/run_all.sh
```
