# Bittesnor: demo-ready build plan (localnet E2E, then Render + Vercel on testnet)

## Context

The core subnet already works on a localnet: miner pools issue tickets and store runs
([miner/app.py](miner/app.py)), the validator replays in native MuJoCo, gates on replay drift,
success and dedup, scores, sets weights and commits epoch Merkle roots
([validator/pipeline.py](validator/pipeline.py), [validator/main.py](validator/main.py)), the web app
records runs in WASM MuJoCo, and [export/lerobot_export.py](export/lerobot_export.py) writes a
LeRobotDataset (lerobot 0.6.1). Nothing is live: no testnet, no hosting, players are free-text
nicknames, and the score is a 5-part quality blend times demand and novelty that is hard to explain.

Goal: a demo where anyone signs in with Google, the backend creates and pays for their own
registered miner on the subnet, they play on a phone, a validator scores the run with a simple
time + smoothness formula, weights land on chain, and accepted runs export to LeRobot format.
First proven end to end on localnet on the Mac, then deployed: frontend on Vercel, backend
(hosted miner service, validator, Postgres) on Render, chain on Bittensor testnet.

Decisions from the user (Oct 30):
- Score = time + jerk (smoothness). Nothing else in the value.
- Web2 onboarding: Google sign-in through **Clerk**, custodial wallet per player, keys encrypted in our Postgres.
- Every player is registered as a real miner (own hotkey, own UID). **The backend treasury pays the
  registration** (transfer plus burn), the player pays nothing.
- Vercel for the frontend, Render for the backend.
- Frontend revamp: landing + play + live network page.

## Architecture after this change

```
 Phone / desktop (Vercel static site)
   |  Clerk session JWT as Bearer
   v
 Hosted miner service (Render web service, FastAPI)            Postgres (Render)
   - /me, /ticket, /submit  (per player)  <--->  users, encrypted keys
   - /m/{hotkey}/trajectories|verdicts  (validator, http_auth signed)
   - /network, /leaderboard  (public read)
   - registrar thread: treasury -> transfer -> burned_register (one per block)
   |
   v  pulls per player hotkey               Bittensor testnet (chain)
 Validator (Render background worker) ----> set_weights over player UIDs, epoch Merkle commitments
   - writes accepted runs to disk -> LeRobot export job (CLI, optional push to Hugging Face)
```

One backend process serves every player's miner hotkey. The chain sees N miners; the validator
reaches them all at `HOSTED_MINER_URL/m/{hotkey}`.

## Phase 1: simple scoring formula

Files: [validator/quality.py](validator/quality.py), [validator/scoring.py](validator/scoring.py),
[validator/pipeline.py](validator/pipeline.py), [validator/store.py](validator/store.py),
[common/schema.py](common/schema.py) (Verdict), `common/tasks/*.json`,
[scripts/dev/practice.py](scripts/dev/practice.py), [web/src/types.ts](web/src/types.ts).

- `time_score = min(1, ref_seconds / duration_s)`, `duration_s = steps * CONTROL_DT`. Add
  `ref_seconds` per task JSON (start near 40 s for `rack_vial`, 30 s for `put_cube_in_bowl`, tune
  from real runs). Recording starts at first input, so idle start time is not counted.
- `smooth_score = exp(-jerk_rms / JERK_SCALE)`: reuse `_smoothness` from quality.py as is.
- `score = 0.5 * time_score + 0.5 * smooth_score` (weights as named constants). Value of an accepted
  run = score. Rejected runs are 0.
- Gates stay unchanged: ticket checks, replay drift, success on replay, near duplicate rejection.
- Miner score per epoch = sum of its accepted values; EMA across epochs stays (`pool_scores`,
  `normalize` in scoring.py are reused, just renamed to miner terms).
- Delete demand, novelty, diminishing returns and the other four quality parts. Verdict carries
  `time_score`, `smooth_score`, `score`, `duration_s` instead of `quality` / `novelty`.
  Store columns change accordingly (fresh validator DB; local `data/` is wiped before E2E).
- Module docstring states the formula in one line so the deck and docs can quote it.

## Phase 2: accounts, custodial wallets, backend-paid registration

New package `accounts/` (kept small, one concern per file):

- `accounts/keys.py`: generate coldkey and hotkey mnemonics with `bittensor_core.Keypair.generate_mnemonic`,
  load with `Keypair.create_from_mnemonic`. A frozen `CustodialWallet(coldkey, coldkeypub, hotkey)`
  dataclass satisfies the SDK `KeyedWallet` protocol, so `st.execute` / `st.submit_call` and
  `http_auth` accept it without wallet files. Mnemonics are encrypted with Fernet
  (`WALLET_ENCRYPTION_KEY`, `cryptography` dependency) before they touch the database.
- `accounts/store.py`: SQLAlchemy Core on `DATABASE_URL` (Postgres on Render, Postgres in Docker
  locally). Tables: `users` (id, clerk_user_id unique, email, display_name, coldkey_ss58, hotkey_ss58,
  enc_coldkey, enc_hotkey, uid, reg_status `pending|funding|registering|registered|failed`,
  reg_error, created_at) (no sessions table, Clerk owns sessions).
- `accounts/clerk.py`: verify the Clerk session JWT (RS256) with PyJWT `PyJWKClient` against
  `CLERK_JWKS_URL`, checking `iss == CLERK_ISSUER`, `exp`/`nbf`, and `azp` in the allowed origins.
  `sub` is the Clerk user id. Display name and email come from the Clerk Backend API
  (`GET /v1/users/{id}` with `CLERK_SECRET_KEY`) once, on first login. A dev login
  (`AUTH_DEV_LOGIN=1`) exists for localnet scripts only and refuses to start when `CHAIN_ENDPOINT`
  is `test` or `finney`. No local session table: Clerk owns sessions.
- `accounts/registrar.py`: one background thread, one registration at a time:
  1. read the current subnet burn; stop with a clear `reg_error` if it is above `MAX_BURN_TAO`
     or the treasury balance is short;
  2. treasury coldkey `bt.Transfer`s burn plus a fee margin to the player's coldkey;
  3. player coldkey submits `burned_register(netuid, hotkey)`; use the raw `bt.calls` fallback
     pattern already in [common/chain.py](common/chain.py) where the intent preflight fails;
  4. look up the UID, mark `registered`.
  Guards: `MAX_SIGNUPS_PER_DAY`, max UIDs headroom check, retry with backoff on rate limit errors.
- [common/chain.py](common/chain.py) gains `transfer`, `burned_register`, `burn_cost`,
  `uid_of(hotkey)`, `balance(coldkey)`, all with the existing `_must` result checking. Exact SDK
  read keys are confirmed against bittensor 11.3 at implementation time.
- Treasury, owner and validator keys load from env mnemonics (`TREASURY_MNEMONIC`, ...) on Render,
  from `~/.bittensor/wallets` locally.

## Phase 3: hosted multi-tenant miner and validator changes

[miner/app.py](miner/app.py) (split into routers so no file passes ~300 lines:
`miner/routes_player.py`, `miner/routes_validator.py`, `miner/routes_public.py`):

- The first authenticated call (`GET /me`) upserts the user, creates the wallet and queues registration.
  `GET /me` -> name, ss58 addresses, UID, registration status, accepted runs, total score, on-chain
  incentive and emission.
- `GET /ticket` and `POST /submit` require a session. Tickets are built with the player's hotkey
  via the existing `build_ticket`. Submit checks `ticket.hotkey == user.hotkey`, then the backend
  signs `bundle_id` with the player's hotkey and stores the signature next to the bundle.
  Per-user rate limits on top of the per-IP ones in [miner/ratelimit.py](miner/ratelimit.py).
- `GET /m/{hotkey}/trajectories`, `POST /m/{hotkey}/verdicts`: `http_auth.verify` with
  `self_hotkey_ss58=hotkey`, hotkey must be one we manage, caller must hold a validator permit
  (existing `validator_keys()` logic).
- [miner/db.py](miner/db.py): add `hotkey` to `tickets` and `bundles`; `bundles_since` filters by hotkey.
- Public: `GET /network` (miners with UID, incentive, emission, weights from the validator,
  recent verdict feed, latest epoch roots read from chain commitments, cached 15 s) and
  `GET /leaderboard` keyed by player.
- [validator/main.py](validator/main.py): `miner_url` falls back to `HOSTED_MINER_URL` + `/m/{hotkey}`
  when a neuron has no override or endpoint; skip the owner and itself. The pipeline verifies the
  per-run hotkey signature (reject "run not signed by the miner hotkey"). The existing
  `ticket_problem` hotkey check already binds the ticket to the neuron being pulled.
- Pool wallets `pool-open` / `pool-two` and second-pool UI are retired.

## Phase 4: LeRobot dataset

[export/lerobot_export.py](export/lerobot_export.py) already writes LeRobotDataset v0.6.1 with
SO-101 feature names, front camera video and the task string. Changes:
- Provenance rows add `miner_hotkey`, `uid`, `time_score`, `smooth_score`, `score`, `duration_s`
  (read from the validator store next to the accepted JSON).
- Add `observation.images.top` when the scene has that camera (check `assets/so101` cameras).
- `--push REPO_ID` flag that calls `push_to_hub` using `HF_TOKEN`.
- Verify by loading the output with `LeRobotDataset(repo_id, root=out)` and iterating a batch, and
  by opening it in lerobot's dataset visualizer.

## Phase 5: localnet end-to-end on the Mac (gate before any deploy)

- [scripts/localnet/up.sh](scripts/localnet/up.sh): also start a Postgres container.
- [scripts/localnet/setup.py](scripts/localnet/setup.py): fund owner, validator and treasury from
  the dev account, create and start the subnet, register and stake the validator. No pool wallets.
  [scripts/localnet/tune.py](scripts/localnet/tune.py) as today, plus raise registrations per block
  if the localnet needs it.
- New `scripts/localnet/run_all.sh`: starts the hosted miner, validator and `npm run dev` with the
  right env, logs to `data/logs/`.
- [scripts/dev/sim_phone.py](scripts/dev/sim_phone.py): log in through the dev login so it acts as
  several distinct players (several registrations, several miners).
- A Clerk application (dev instance) with Google enabled as a social connection and `http://localhost:5173` allowed. The dev instance uses Clerk's shared Google credentials, so no Google OAuth client is needed. User supplies `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`.

E2E checklist, all must pass:
1. Clerk Google sign-in on localhost creates a user, encrypted keys appear in Postgres, the treasury
   balance drops by burn plus fee, and the player's hotkey gets a UID.
2. Play a `rack_vial` run, submit, verdict shows time, smoothness and score.
3. Tampered run (edited ctrl) and reused ticket are rejected with reasons.
4. `sim_phone.py` with 3 players: each gets its own UID, validator sets weights across all of them,
   epoch root committed, `/network` shows it.
5. Export the accepted runs to LeRobot and load them back.

## Phase 6: frontend revamp

Run the frontend-design skill first for direction. Keep vanilla TS + Vite (no framework change) as
a Vite multi-page build:
- `index.html` landing: what the subnet does, 3 step how-it-works, live stats strip from `/network`,
  Sign in with Google via `@clerk/clerk-js`.
- `play.html`: the current simulator, restyled. Signed-in header with miner status chip
  ("Registering your miner", "Miner UID 12"). Result screen shows the formula breakdown
  (time, smoothness, score) and the player's rank. Split [web/src/main.ts](web/src/main.ts) into
  `play/round.ts`, `play/hud.ts`, `play/result.ts`, keeping existing controls, joysticks and
  fullscreen code.
- `network.html`: live verdict feed, miner leaderboard (UID, score, incentive), validator weights,
  epoch Merkle roots with testnet explorer links, dataset link.
- New `web/src/auth.ts` (token in localStorage wrapped in try/catch, Bearer header in
  [web/src/api.ts](web/src/api.ts)).
- Rerun the Phase 5 checklist after the revamp, including a real phone over
  [scripts/demo/tunnels.sh](scripts/demo/tunnels.sh).

## Phase 7: deploy (Render + Vercel) and go live on testnet

- `render.yaml` blueprint: web service `bittesnor-miner` (Docker from
  [deploy/Dockerfile](deploy/Dockerfile), persistent disk for bundles), background worker
  `bittesnor-validator` (same image, disk for its SQLite and accepted runs), Postgres
  `bittesnor-db`. Starter plans, since free instances sleep and the validator must stay up.
  Secrets: `WALLET_ENCRYPTION_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `CLERK_ISSUER`, treasury and validator mnemonics,
  `HF_TOKEN`. Validator gets `HOSTED_MINER_URL` = the Render miner URL.
- `web/vercel.json`: build `npm run build`, output `dist`, rewrite `/pool/:path*` to the Render
  miner (same origin, so no CORS or mixed content), rewrites for `/play` and `/network`. Add the
  Vercel domain to the Clerk allowed origins (production instance on testnet) and `MINER_ALLOWED_ORIGINS`.
- [scripts/testnet/setup.py](scripts/testnet/setup.py): owner, validator, treasury; check the
  subnet lock cost before creating; set owner hyperparameters (weights rate limit, registrations
  per block, burn bounds) where the owner is allowed to.
- Start the 24 hour run at least a day before the demo. Update [docs/runbook.md](docs/runbook.md),
  [docs/demo-script.md](docs/demo-script.md), README.

## Risks to watch

- **Testnet TAO budget.** Subnet lock cost plus burn per player. Burn rises with registrations, so
  `MAX_BURN_TAO` and `MAX_SIGNUPS_PER_DAY` cap the spend. Need the faucet amount before Phase 7.
- **256 UID cap and pruning.** New registrations prune low-scoring miners after the immunity
  period. Fine for a demo; the registrar refuses when no slot is free.
- **Custodial keys.** Testnet only. Losing `WALLET_ENCRYPTION_KEY` loses every player key.
- **Registration latency.** Transfer plus register takes about two blocks (~24 s on testnet).
  Players can start playing immediately; the run is scored once the UID exists.
- **Commit-reveal on testnet.** The SDK `SetWeights` intent handles it; verified in Phase 7.

## Commits

One commit per phase step, `<type>: <description>`, no attribution lines (CLAUDE.md). No tests
or TDD (CLAUDE.md overrides the global testing rules); verification is by running the real flow.

## Verification

Phase 5 checklist on localnet, repeated after Phase 6 and on a real phone, then on testnet after
Phase 7: sign in on the Vercel URL from a phone, see the UID appear on the testnet explorer, play,
see the verdict, see weights and the epoch root on chain, export and load the LeRobot dataset.
