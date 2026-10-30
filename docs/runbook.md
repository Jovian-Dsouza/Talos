# Runbook

All commands run from the repository root unless noted. Python 3.12 with uv, Node 20 or newer,
Docker for the localnet.

## 0. Try it on your desktop (no chain)

```
uv run --python 3.12 python scripts/dev/practice.py        # judge on port 8091
cd web && npm install && npm run dev                        # app on http://localhost:5173
```

Open `http://localhost:5173/?pool=http://127.0.0.1:8091`. The practice server hands out tasks and
judges each run with the real replay, success check and scoring, with no Bittensor involved.

Pick a task on the start card. Vial racking (lab automation) asks for a named sample vial to be seated
in a named slot of a 2 by 4 rack among vials already racked. Parts to tote (logistics) moves a named
part into the matching tote. Both are judged by the same replay pipeline.

Controls on a phone, or on a desktop after pressing Joysticks:

- Left stick moves the gripper over the bench, relative to the camera, so up is away from you.
- Right stick up and down raises and lowers the gripper, left and right rolls the wrist.
- Grip toggles the gripper closed and open. A mouse can still hold the button.
- One finger on the scene orbits the camera, two fingers zoom and pan. Cam cycles Front, Overhead
  and Side, Views hides the two inset views, Full screen helps on tablets. Hold a phone sideways
  for the biggest view.

Controls on a desktop without sticks: drag on the scene to move the blue target ring and the arm
follows. Height slider or Q and E raise and lower the gripper. Hold the Hold to grip button or
Space to close the gripper. Left and right arrows roll the wrist. W, S, A, D nudge the target.

Nothing records until your first input. Typical run: hover over the part, lower to the bench, grip,
lift, move over the goal, lower a little, release, then Submit. For vials, grip about mid height and
lower the vial straight into the hole before releasing. The yellow arc on the bench marks the arm's
reach, and the shelving, signal tower and bench are scenery only: they never affect the physics.

## 1. Local chain and subnet

```
scripts/localnet/up.sh
uv run --python 3.12 python scripts/localnet/setup.py
uv run --python 3.12 python scripts/localnet/tune.py 2
```

`setup.py` funds wallets from the development account, creates the subnet (look for the printed
netuid, normally 2 on a fresh chain), registers the owner (uid 0), validator (uid 1), open pool
(uid 2) and second pool (uid 3), starts the subnet and stakes the validator. `tune.py` turns off
commit-reveal and the weights rate limit, which the Docker localnet needs for plain set_weights.
Run `setup.py` once per fresh chain. To reset: `docker rm -f bittesnor-localnet`, then repeat.

## 2. Miners

One process per pool. The endpoint is published on chain with the public IP, which must not be a
loopback address (the chain rejects 127.0.0.1), so use the machine's LAN or public IP.

```
export NETUID=2 MINER_PUBLIC_IP=<lan or public ip> MINER_VALIDATOR_ALLOWLIST=<validator hotkey ss58>
MINER_DATA_DIR=data/miner-open uv run --python 3.12 python -m miner.main
MINER_WALLET=bittesnor-pool-two MINER_PORT=8092 MINER_DATA_DIR=data/miner-two uv run --python 3.12 python -m miner.main
```

Environment: `CHAIN_ENDPOINT` (default `ws://127.0.0.1:9944`, use `test` for testnet),
`TASK_IDS` (comma list of tasks this pool serves, the first is the default, default
`rack_vial,put_cube_in_bowl`; the app reads `GET /tasks` and `GET /ticket?task=ID`),
`MINER_ALLOWED_ORIGINS` (comma list, default any), `MINER_TRUST_PROXY=1` behind a tunnel or CDN so
rate limits key on the real client address. Validators are recognized by validator permit on chain,
plus anything in `MINER_VALIDATOR_ALLOWLIST` (needed on localnet until the permit appears).

## 3. Validator

```
POLL_SECONDS=2 uv run --python 3.12 python -m validator.main
```

Environment: `REPLAY_MODE` (`strict` or `windowed`), `EPS_ARM` (0.01 rad), `EPS_OBJECT` (0.005 m),
`TEMPO_BLOCKS` (epoch length for scoring and Merkle roots, 10 on localnet, 360 on testnet),
`WEIGHTS_EVERY_BLOCKS`, `MINER_URLS` (`hotkey=url,...` overrides for miners without an on-chain IP),
`DEMAND_FILE` (JSON of task to demand multiplier, 1 to 5), `ACCEPTED_DIR` (accepted recordings,
the export input), `VALIDATOR_DB`.

Per recording the validator checks the ticket (seed, scene, block hash on chain, expiry, one use),
replays the controls in native MuJoCo 3.17.0 and compares recorded checkpoints, runs the success
check on its own replayed state, rejects near duplicates, scores quality and novelty, and records
the verdict. Every tempo it sets weights from per-pool EMA scores and commits the previous epoch's
Merkle root on chain.

## 4. Web app

```
cd web
npm install
npm run dev          # development, http://localhost:5173
npm run build && npm run preview   # production build on port 4173
```

Open `/?pool=http://<miner>:8091&pool2=http://<miner2>:8092`. `pool` is where the player records
and submits; both pools feed the leaderboard comparison. `VITE_EXPLORER_URL` at build time adds the
"see the weights on chain" link. For a CDN deploy, upload `web/dist`; the miner must allow the
site's origin in `MINER_ALLOWED_ORIGINS`.

The visual meshes in `web/public/assets/so101` are decimated copies. Regenerate with
`uv run --python 3.12 --with trimesh --with fast-simplification python scripts/assets/decimate.py web/public/assets/so101`.
Physics is bit-identical to the full meshes because collision and mass meshes are copied untouched.

## 5. Phones over HTTPS

iOS and Android only deliver tilt events on HTTPS, and an HTTPS page cannot call an HTTP miner. So
both the web app and the miner need HTTPS URLs. `scripts/demo/tunnels.sh` starts two Cloudflare
quick tunnels and prints the phone URL with a QR code. It publishes local services to the internet,
so run it deliberately and stop it afterwards. Set `MINER_TRUST_PROXY=1` on the miner first.
For a real deployment host `web/dist` on a CDN and put the miner behind a TLS reverse proxy.

## 6. Dev tools

`scripts/dev/sim_phone.py URL COUNT CONCURRENCY NAME` acts like phones using a scripted solver:
ticket, solve, submit, wait for the verdict. Use it for load runs. The scripted solver produces
near identical normalized paths, so many of its runs are rejected as duplicates, which is the
dedup working as intended.

## 7. Export and real arm

```
uv run --python 3.12 --extra export python -m export.lerobot_export data/accepted out/sample bittesnor/teleop-so101-sim-sample
```

Writes a LeRobotDataset (state, action, front camera video, task string per episode) plus
`meta/teleop_provenance.jsonl` with seed, pool, contributor and scene per episode. Push it with
`huggingface-cli upload` after logging in. Real arm replay and calibration: [real-arm.md](real-arm.md).

## 8. Testnet

1. Get testnet TAO (Bittensor Discord faucet). About 1 TAO creates the subnet; registrations and
   validator stake need a few more.
2. `uv run --python 3.12 python scripts/testnet/setup.py` creates wallets, the subnet, registers
   neurons and stakes the validator. Fund each coldkey first (the script prints the addresses).
3. On the VM: put `NETUID`, `CHAIN_ENDPOINT=test`, `MINER_PUBLIC_IP` and `VALIDATOR_HOTKEY_SS58`
   in `deploy/.env`, then `docker compose -f deploy/docker-compose.yml up -d --build`.
4. Start the 24 hour run at least a day before the demo so emission history exists. With the
   default tempo of 360 blocks (about 72 minutes) emissions arrive once per epoch.

Testnet differences from localnet: the SDK `SetWeights` intent handles commit-reveal, so the raw
fallback in `common/chain.py` should not trigger. Disabling commit-reveal is a subnet owner
hyperparameter if the intent misbehaves.

## 9. Failure drills (all verified on localnet)

- Miner down: the validator logs the failed pull and carries on with the other pools.
- Malformed, oversized or unsigned requests get 400, 413 and 401. Tickets are single use (409).
- Forged checkpoint, edited controls, wrong seed, wrong pool, reused ticket: rejected with a reason.
- Burst of 20 simultaneous phones: all verdicts returned in about 12 seconds on one validator core.
