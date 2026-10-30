# Hackathon submission checklist

Use this list before you submit and before the live demo. Commands and architecture live in
[runbook.md](runbook.md), [demo-script.md](demo-script.md), and [teleop-subnet-plan.md](../teleop-subnet-plan.md).

**Judging bar (from the hackathon brief):** working prototype, clear problem and solution, strong
execution, meaningful use of Bittensor, credible path forward.

**Demo success (3 minutes):** judge on phone over HTTPS, seeded task, verdict in seconds, optional
chain weights and Merkle root, LeRobot sample on Hugging Face, optional real SO-101 replay.

---

## Priority legend

| Priority | Meaning |
|----------|---------|
| **P0** | Block submission or live demo if missing |
| **P1** | Strongly improves score and judge experience |
| **P2** | Nice to have; do after P0 and P1 are green |

---

## P0: Blockers (do first)

### P0.1 Testnet TAO and wallets

- [ ] Request **testnet TAO** from the Bittensor Discord faucet (budget about **8 to 10 TAO** on the owner for subnet, registrations, and validator stake).
- [ ] Primary deposit address (owner coldkey, wallet name `bittesnor-owner`):
  - `5Hq2QyfvUjdK6yi5ms2N1E8LLenEvvjmQPkTR5kSMLbfQENw`
- [ ] Confirm wallet files exist locally (private keys stay on disk, never commit or paste):
  - `~/.bittensor/wallets/bittesnor-owner/`
  - `~/.bittensor/wallets/bittesnor-validator/`
  - `~/.bittensor/wallets/bittesnor-pool-open/`
  - `~/.bittensor/wallets/bittesnor-pool-two/`
- [ ] Check owner balance before subnet creation:

```bash
uv run --python 3.12 python -c "
import bittensor as bt
w = bt.Wallet(name='bittesnor-owner', hotkey='default')
print(bt.Subtensor('test').read('balance', coldkey_ss58=w.coldkeypub.ss58_address))
"
```

### P0.2 Create subnet and register neurons

- [ ] Run testnet setup (interactive confirm):

```bash
uv run --python 3.12 python scripts/testnet/setup.py
```

- [ ] Record and store securely for deploy and demo:
  - [ ] `NETUID`
  - [ ] Owner, validator, and both pool **hotkey** SS58 addresses
  - [ ] `CHAIN_ENDPOINT=test`
- [ ] Transfer TAO from owner to other coldkeys if registration fails on empty pool or validator coldkeys.

### P0.3 Run miner and validator in production layout

- [ ] Create `deploy/.env` with at least:
  - [ ] `NETUID=<from setup>`
  - [ ] `CHAIN_ENDPOINT=test`
  - [ ] `MINER_PUBLIC_IP=<VM public IP, not 127.0.0.1>`
  - [ ] `VALIDATOR_HOTKEY_SS58=<validator hotkey>`
  - [ ] `MINER_TRUST_PROXY=1` if behind Cloudflare or a tunnel
- [ ] Start stack:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

- [ ] Verify miner health: `GET https://<miner-host>/health` returns hotkey and block.
- [ ] Verify validator logs: pulling bundles, posting verdicts, no repeated auth failures.
- [ ] Set `MINER_VALIDATOR_ALLOWLIST` until validator permit appears on metagraph (see runbook).

### P0.4 HTTPS for judges' phones

iOS and Android need HTTPS for tilt; an HTTPS page cannot call an HTTP miner.

**Option A (fastest for hackathon):** quick tunnels

- [ ] Build web app: `cd web && npm install && npm run build && npm run preview`
- [ ] Run miner with `MINER_TRUST_PROXY=1` and allowed origins for the tunnel web URL.
- [ ] Run `scripts/demo/tunnels.sh` and save the printed **phone URL** and QR code.
- [ ] Stop tunnels when not demoing (they expose local services).

**Option B (stable URL):** Cloudflare Pages plus pool proxy

- [ ] Deploy `web/dist` to Cloudflare Pages.
- [ ] Proxy `/pool/*` to the miner origin (Worker or tunnel to VM).
- [ ] Set `MINER_ALLOWED_ORIGINS` to the Pages origin.
- [ ] Build with `VITE_EXPLORER_URL` for testnet explorer link in the app.
- [ ] Default pool URL should be same-origin `/pool` on HTTPS (see `web/src/config.ts`).

- [ ] **Physical phone test:** one full run on iOS or Android (ticket, teleop, submit, verdict).

### P0.5 End-to-end data path (human episode, not scripted load)

- [ ] Complete at least **one accepted** recording from the **browser** (real input timing).
- [ ] Confirm verdict: replay OK, success OK, quality and novelty shown.
- [ ] Confirm validator **`ACCEPTED_DIR`** contains a new JSON bundle (Docker volume `validator-data` or path in compose).
- [ ] Avoid relying on `scripts/dev/sim_phone.py` for the main demo dataset (many duplicate rejects).

### P0.6 Hugging Face public sample (submission artifact)

- [ ] Create Hugging Face account and dataset repo (example id: `bittesnor/teleop-so101-sim-demo`).
- [ ] Export accepted episodes:

```bash
uv run --python 3.12 --extra export python -m export.lerobot_export \
  <ACCEPTED_DIR> out/hf-export bittesnor/teleop-so101-sim-demo
```

- [ ] Upload:

```bash
huggingface-cli login
huggingface-cli upload bittesnor/teleop-so101-sim-demo out/hf-export . --repo-type dataset
```

- [ ] Add dataset **README** (task description, SO-101, Bittensor verification, license, link to repo).
- [ ] Open the dataset page in a browser and confirm LeRobot layout: video, state, action, task string.
- [ ] Point to `meta/teleop_provenance.jsonl` (seed, pool hotkey, contributor, scene).

### P0.7 Miner connects wallet and collects data (demo story)

Clarify roles for judges: **miner = pool operator** (Bittensor hotkey on server). **Teleoperator = human** in the browser.

**Pool operator (miner)**

- [ ] Document or show: create or import wallet, `burned_register` on your `NETUID`, run `python -m miner.main` with `MINER_WALLET`.
- [ ] Demo proof: `/health` hotkey matches the registered pool on the subnet.
- [ ] Optional P1: short **miner onboarding** page (extension connect shows SS58 plus env template).

**Teleoperator (data contributor)**

- [ ] Start screen: nickname plus optional **wallet SS58** (paste today; extension connect is P1).
- [ ] Contributor string appears in leaderboard and HF provenance.

- [ ] Second pool (`pool-two`) running if you show **open pool vs second pool** on the leaderboard.

### P0.8 Submission package (what reviewers need without your laptop)

- [ ] **GitHub repo** clean default branch: README explains problem, Bittensor roles, how to run localnet.
- [ ] **Live URL** or clear video fallback if live URL is fragile.
- [ ] **Hugging Face dataset URL** in README and submission form.
- [ ] **Testnet `NETUID`** and explorer links to at least one `SetWeights` or Merkle commit (if chain ran long enough).
- [ ] **One-page architecture** (can be README diagram or deck slide): phone, pool, validator, Subtensor, HF export.
- [ ] **NOTICE** and licenses respected (Menagerie SO-101, no Axis code copy).

---

## P1: Strong demo and judging score

### P1.1 Chain history before demo day

- [ ] Start testnet stack **at least 24 hours** before demo (tempo about 72 minutes on testnet).
- [ ] Confirm at least one **weights** extrinsic and **epoch Merkle root** commitment on explorer.
- [ ] Second device or tab: validator logs plus explorer for step 5 of [demo-script.md](demo-script.md).

### P1.2 Rehearsal

- [ ] Run through [demo-script.md](demo-script.md) twice with a friend as judge.
- [ ] Time each segment (target about 3 minutes).
- [ ] Prepare **talking points:** seed-bound tickets, replay verification, duplicate rejection, LeRobot parity with real SO-101, demand multiplier story.
- [ ] QR code printed or on slide pointing to **HTTPS phone URL** only.

### P1.3 Wallet UX (browser)

- [ ] Talisman or SubWallet **connect** on start screen to fill SS58 (replace paste-only).
- [ ] Miner onboarding doc: `docs/miner-onboard.md` or runbook section (register, env, compose).

### P1.4 More dataset credibility

- [ ] **3 or more** accepted human episodes from different contributors or devices.
- [ ] Re-export and re-upload Hugging Face before submission deadline.
- [ ] Include both tasks if possible: `rack_vial` and `put_cube_in_bowl`.

### P1.5 Real arm (if hardware ready)

- [ ] Calibrate per [real-arm.md](real-arm.md) and `realarm/mapping.json`.
- [ ] Replay one accepted bundle: `SPEED=0.5 uv run --extra realarm python -m realarm.replay_episode <bundle> <port>`.
- [ ] Fallback video on disk if venue USB or Wi-Fi fails.

### P1.6 Failure drills (confidence on stage)

Run once on testnet or localnet (runbook section 9):

- [ ] Stop one miner: validator logs error, other pool still works.
- [ ] Submit with bad ticket: clear rejection reason in UI.
- [ ] Burst load optional: `scripts/dev/sim_phone.py` for leaderboard filler only.

---

## P2: After submission or if time remains

- [ ] Automated HF publish script (watch `ACCEPTED_DIR`, export, upload on schedule).
- [ ] Cloudflare named tunnel instead of trycloudflare quick URLs.
- [ ] Signed contributor messages on submit (cryptographic attribution).
- [ ] Cold outreach plus open sample link ([outreach.md](outreach.md)).
- [ ] Localnet backup screen for fast block emissions during Q&A.
- [ ] Mainnet subnet planning (~440 TAO), encrypted wallets, monitoring.

---

## Demo morning (day of submission)

- [ ] Health check: miner `/health`, validator polling, web URL loads WASM.
- [ ] Fresh human episode if last accept is old; refresh HF upload if needed.
- [ ] Charge phones; test venue Wi-Fi or use cellular plus HTTPS URL.
- [ ] Start tunnels or confirm Pages plus proxy if using Option A or B.
- [ ] Backup: localnet on laptop, recorded demo video, pre-exported HF revision hash.

---

## Fallback matrix (if something breaks on stage)

| Failure | Fallback |
|---------|----------|
| Testnet down | Localnet plus runbook section 1; explain same code path |
| Phone HTTPS broken | Judge uses laptop with joysticks mode |
| No new accept | Show last accepted verdict recording plus HF dataset |
| No weights yet | Show validator log and Merkle commit or localnet weights tx |
| Real arm fails | Video of prior successful replay |
| Quiet room | `sim_phone.py` for leaderboard motion only; explain dedup rejects |

---

## What is already built (do not rebuild)

- Miner API (tickets, submit, signed validator pull, leaderboard)
- Validator replay, scoring, dedup, weights, Merkle epochs
- Web teleop (MuJoCo WASM 3.17, tasks, verdict UI)
- LeRobot export pipeline
- Docker compose and testnet setup scripts
- `sim_phone.py` is **load test only**, not subnet integration

---

## Quick reference: owner wallet

| Item | Value |
|------|--------|
| Wallet name | `bittesnor-owner` |
| Coldkey (fund here first) | `5Hq2QyfvUjdK6yi5ms2N1E8LLenEvvjmQPkTR5kSMLbfQENw` |
| On disk | `~/.bittensor/wallets/bittesnor-owner/` |

Never share the `coldkey` file or seed. Only share the public SS58 for faucet deposits.

---

## Submission form checklist (typical fields)

- [ ] Project name and one-line pitch (verified sim teleop data subnet, LeRobot export).
- [ ] Repository URL.
- [ ] Live demo URL (HTTPS web app).
- [ ] Hugging Face dataset URL.
- [ ] Testnet subnet id (`NETUID`) if applicable.
- [ ] Team contacts.
- [ ] Short video link (recommended if live demo is optional for submission).
- [ ] How Bittensor is used: pools as miners, validators replay and set weights, on-chain Merkle roots.

---

*Last aligned with repo state and [teleop-subnet-plan.md](../teleop-subnet-plan.md) implementation status. Update checkboxes as you complete items.*
