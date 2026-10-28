# Teleop Data Subnet: Plan v1

*October 26, 2026. Builds on [robotics.md](robotics.md) and [bittesnor.md](bittesnor.md). Decisions are recorded in Section 9.*

---

## 1. The idea in one paragraph

People drive a simulated **SO-101 robot arm** on their phone or laptop. Physics runs on their device (MuJoCo in the browser). Each recording is a candidate demonstration. Bittensor validators **replay it themselves** in native MuJoCo to confirm it really happened and really succeeded, score its quality and novelty, and reject duplicates. Miners are **pools** that recruit and pay humans and earn emissions in proportion to verified, useful data. The company that owns the subnet sells the verified dataset to **VLA / foundation-model labs** and uses the revenue to fund task bounties and buy back the subnet token, so **buyer demand steers where miners spend effort.**

---

## 2. What the research says

### Axis Robotics today (Oct 2026)
- 229k+ contributors, 7.3M+ trajectories, 1,600+ tasks, 7.0M on-chain records on Base ([docs](https://docs.axisrobotics.ai/)).
- $12M seed (Hack VC). AXIS token with a public sale and Binance Alpha airdrop. Points are non-transferable and counted per two-week epoch.
- **Already in the Bittensor ecosystem:** contributed 3M+ trajectories to the Open Data Pool of OpenRoboto (SN80) ([CryptoBriefing](https://cryptobriefing.com/openroboto-shift-decentralized-robotics-data-bittensor/)).
- Partners named: AgiBot, Booster, Zeroth, Deep Robotics, EngineAI, Unitree. No public pricing ([partners page](https://docs.axisrobotics.ai/solutions/partners.md)).

### Other competitors
| Who | What | Overlap with us |
|---|---|---|
| **OpenRoboto SN80 "Shift"** | Pays for egocentric video. Miners fine-tune π0.5. | Possible **customer** (their miners need training data) and an adjacent competitor. |
| **PrismaX** ($11M, a16z CSX) | Teleop marketplace selling teleop + egocentric data. | Direct competitor for buyers. |
| **BitRobot / FrodoBots** | Solana "subnets"; first subnet is browser teleop of real sidewalk rovers. | Same "subnet" pitch, but on Solana and with real robots. |

### What buyers pay (indicative only, vendor sources)
- Real teleop: **$28–60/raw hr**, **$90–200 per usable hr** fully loaded in the US ([DexSet](https://dexset.ai/blogs/robot-training-data-costs-pricing-complete-2026/)).
- Egocentric video: $15–60/hr.
- **No public price exists for browser-sim trajectories.** This is the single biggest unknown and must come from customer conversations.
- Research consensus: sim data helps a lot in pre-training and co-training (a reported ~3:1 sim:real mix), but pure sim is not enough for deployment.

### Cost to launch
| | Subnet creation (lock cost, queried live Oct 26) |
|---|---|
| Testnet | **1 testnet TAO** |
| Mainnet | **~440 TAO** (≈ $140k at the ~$318/TAO implied by SN80's token quote) |

---

## 3. Where Axis falls short and how we beat it

| Axis weakness | Evidence | Our answer |
|---|---|---|
| **Quality is judged centrally and opaquely.** On-chain records prove *provenance*, not *quality*. | Docs: each trajectory gets a Data ID on Base; quality checks run on Axis servers. | **Trustless verification:** independent validators replay every trajectory in native MuJoCo and agree via Yuma Consensus. |
| **Volume ≠ policy-ready data.** | Their own open-source training repo: the task 3801 policy finished training but *"failed its one-scene closed-loop Checker gate"* ([Axis-V1-Training](https://github.com/AxisAIOrg/Axis-V1-Training)). | Score for usefulness, not count. Later phases add a "does this data improve a policy" bonus. |
| **Keyboard 6-DOF control produces jerky data** that needs heavy cleaning. | Tech report: cleaning cut mean acceleration 54% and jerk 47%, and dropped ~5% of frames. | **Phone-as-controller** (drag for position, tilt for the wrist). COBALT found phone teleop matches specialized hardware. |
| **Sim-only: no proof the data works on hardware**, apart from showcase results. | Sim-to-real results published only as case studies. | **Same action space as real SO-101 LeRobot datasets.** Verified sim demos can be replayed on a real arm, as the live demo shows. |
| **Many catalog tasks are ones a scripted planner can solve for free** (close box, pick mug). | Task catalog / example tasks. | Focus on **human-advantage tasks**: language-conditioned variety, long-horizon, recovery and correction. |
| **Rewards are disconnected from sales.** Points → speculative token, decided by the company. | Points/epoch + airdrop model. | **Demand-weighted emissions:** paid buyer bounties raise a task's multiplier. Revenue buys back alpha. |
| **Airdrop farming attracts low-effort users.** | Inference from the points/airdrop design; no direct evidence found. | Seed-bound tasks, replay checks and dedup make farming unprofitable (Section 5). |

### What we reuse (license-checked)
| Repo | License | Use |
|---|---|---|
| [AxisWebInfra](https://github.com/AxisAIOrg/AxisWebInfra): Next.js 16 + MuJoCo WASM, numeric IK, checkers, trajectory recorder | **Apache-2.0** | **Fork** as the frontend. Keep LICENSE + NOTICE + attribution. |
| [AxisDataCleaning](https://github.com/AxisAIOrg/AxisDataCleaning): Savitzky-Golay + spline resampling, jerk/acceleration metrics | **Apache-2.0** | Reuse metrics in the validator's quality score. |
| [Menagerie `robotstudio_so101`](https://github.com/google-deepmind/mujoco_menagerie/tree/main/robotstudio_so101) | **Apache-2.0** | The robot model. |
| [LeRobot](https://huggingface.co/docs/lerobot/en) 0.6.1 | Apache-2.0 | Dataset export + real-arm replay. |
| AxisTaskGen, Axis-V1-Training | **No license** = all rights reserved | Ideas only. Do **not** copy code. |

---

## 4. Who buys, and what they would pay for

| # | Buyer | What they buy | Status |
|---|---|---|---|
| 1 | **VLA / foundation-model labs** | Large, diverse, language-conditioned *human* demo sets for pre-training and co-training; **correction data** on their policy's failure cases | **First target.** The LeRobot / SmolVLA ecosystem is SO-100/101-heavy, so SO-101-format data is immediately usable. |
| 2 | Robot hardware makers without big data teams | "Your robot in sim + demos + baseline policy" | Phase 2 (needs per-robot onboarding). |
| 3 | Bittensor policy subnets (SN80, Kinitro, Nepher) | Training data and human baselines | Partnership / narrative. |
| 4 | Benchmark / eval builders, academic labs | Human baselines, eval episodes | Opportunistic. |

**Offer:** open sample on Hugging Face (credibility) → paid full datasets → **custom task bounties** (lab supplies a task spec, the subnet collects to quota).

**What VLA labs need from each episode:** a natural-language instruction, scene randomization, a success label, consistent action space and rate, metadata (seed, task version, contributor pool), and later failure/recovery segments.

**What NOT to sell:** simple pick-and-place with no variety. Generators like MimicGen produce it for free.

**Selling point vs egocentric players:** sim data contains no faces, homes or voices, so there is no consent or DPDP exposure.

---

## 5. Subnet mechanism

### Roles
| Role | Does | Earns |
|---|---|---|
| **Teleoperator (human)** | Drives the robot in the browser | Paid by their pool (alpha or fiat) |
| **Miner = pool** (a UID) | Issues tasks to its humans, collects recordings, serves them to validators, pays its humans | Emissions ∝ verified value |
| **Open pool** (a UID we run) | Same, for retail users; pays alpha pro-rata to each contributor's wallet | Emissions, passed through |
| **Validator** | Pulls recordings, replays, scores, dedups, sets weights | Validator emissions + dividends |
| **Subnet owner (us)** | Task registry, buyer bounties, dataset packaging and sales | Owner emissions + **external revenue** |

Pools exist because a subnet has 256 UID slots by default. One human per UID cannot scale.

### Seed-bound tasks (the core anti-cheat)
```
seed = H(block_hash[recent] ‖ miner_hotkey ‖ task_id ‖ counter)
```
- Object positions, colors, distractors **and the language instruction** are generated from the seed.
- Any validator can recompute the seed. No coordination needed.
- Replaying an old recording on a new seed fails the success check. Copying another pool's recording fails, because their hotkey is in the seed.
- Recordings expire once the block hash is older than ~2 tempos.

### Validation pipeline (per recording)
1. **Format + ticket check:** the seed derives correctly, the block is fresh, and `(hotkey, task, counter)` has never been used.
2. **Deterministic replay:** native MuJoCo 3.17.0 (same version as the browser build) re-runs the recorded controls from the seeded scene. State drift at each checkpoint must stay within ε.
3. **Success check** on the *replayed* state. The browser's own "success" flag is never trusted.
4. **Duplicate / near-duplicate check:** the gripper path is resampled and compared with recent accepted paths for that task.
5. **Quality:** smoothness (jerk), path efficiency vs the task median, idle ratio, hard collisions, gripper chatter.
6. **Human-likeness (phase 2):** raw input events are recorded. Human touch and tilt input has a tremor and timing signature that scripts don't.

**Policy:** human demonstrations only (stated in the rules). Stage 6 enforces it after the hackathon.

### Scoring
```
V(t) = Gate(t) × Demand(task) × Quality(t)^α × (1 + β·Novelty(t))
Score(pool) = EMA over epochs of Σ V(t), with diminishing returns per task
weights = normalize(Score)   →   bt.SetWeights each tempo
```
- **Gate:** 0/1 from steps 1–4.
- **Demand:** 1× for the base catalog, up to ~5× for paid bounties; decays as the bounty quota fills.
- **Novelty:** capped, so odd paths get no reward just for being odd.

### Data custody and provenance
- Pools upload accepted bundles to the subnet's dataset bucket under a contributor license grant.
- Each epoch, **one Merkle root** of accepted trajectory hashes is committed on-chain. Same provenance as Axis's per-trajectory records at a fraction of the cost.
- Export: **LeRobotDataset** with SO-101 feature names (`shoulder_pan.pos` … `gripper.pos`). Camera frames are rendered server-side during replay.

### Revenue flywheel
```
Lab pays for a task bundle ─► owner converts part to alpha buyback ─► alpha price ↑ ─► subnet emissions ↑
        │                                                                                  │
        └──► Demand multiplier on that task ─► pools shift effort to it ─► verified data ◄─┘
```

---

## 6. Hackathon POC

### Live demo story (judges use their own phones)
1. A judge scans a QR code → the web app opens over HTTPS → they enter a nickname (pasting a wallet address is optional).
2. They get a **seeded, language-conditioned task**: *"Put the red cube in the blue bowl"*, with randomized positions and distractors.
3. They drive the SO-101 with their phone (drag to move, slider for height, tilt for the wrist, button for the gripper).
4. Within seconds the **validator's verdict** appears: replayed ✔, success ✔, quality 0.82, novelty 0.4, or a clear rejection reason.
5. The **leaderboard** updates: the judge's share inside the open pool, the open pool vs a second pool, and the validator's weights transaction on the testnet explorer.
6. **Real arm moment:** we take a just-verified trajectory and replay it on the physical SO-101 via LeRobot. *"Your demo, verified by the network, running on a real robot."*
7. Closing: the accepted data is already a LeRobot dataset; show the open sample on Hugging Face.

**Testnet timing caveat:** with default tempo (360 blocks × 12 s ≈ 72 min), emissions are paid once per epoch, so they won't visibly move during a 3-minute demo. Live on stage: verdict, score, weights tx. Emission history: from running the testnet subnet for at least 24 h before the demo. A fast-block localnet view is the backup "watch it accrue" screen.

### Architecture
```
 Judge's phone / laptop
   static web app on a CDN (Cloudflare Pages / Vercel)
   fork of AxisWebInfra: MuJoCo WASM 3.17 + Three.js, SO-101 with decimated meshes
   Recorder: per-step ctrl, state checkpoints, raw input events, instruction text
          │ HTTPS (public URL)   GET /ticket   POST /submit   GET /status
          ▼
 Open-pool miner node  (Python 3.12, FastAPI, holds pool hotkey)
   derives seeds from latest block hash · contributor attribution (nickname / ss58)
   stores bundles (SQLite + disk) · publishes endpoint (bt.ServeAxon)
   GET /trajectories  ◄── btauth/1 signed, validators only
          ▲
          │  signed pull every few blocks
 Validator node  (Python 3.12, mujoco 3.17)
   seed check → replay → success → dedup → quality → score
   bt.SetWeights each tempo · LeRobot export · per-epoch Merkle root commitment
          │
 Subtensor: localnet (Docker, arm64, fast blocks) for dev → testnet for the demo
          │
 Real-arm station: LeRobot replay of a chosen accepted episode on the physical SO-101
```

**Bittensor 11 note:** Axon/Dendrite/Synapse were removed in SDK 11 (current 11.3.0), and the popular subnet template is archived. We use plain HTTP (FastAPI) + `bt.http_auth.sign/verify` + `bt.SetWeights`.

**Live-demo hardening:** host the static app on a CDN (WASM + meshes are the heavy part). Run the miner and validator on a small cloud VM, with the Mac behind a cloudflared tunnel as fallback. Load-test with ~20 simulated phones. Shrink the SO-101's ~22 MB of STL meshes for phone load times.

### Build plan (5 working days; dates set aside)
| Day | Track A: browser sim | Track B: chain, miner, validator | Track C: real arm, data, pitch |
|---|---|---|---|
| 1 | Fork AxisWebInfra; load SO-101; 5-DOF IK (position + pitch/roll) | **M0 spike: WASM ↔ native replay determinism**; localnet scripts (wallets, subnet, register, stake) | Calibrate the real SO-101 with LeRobot; check the sim↔real joint mapping |
| 2 | Seeded task generator (positions, colors, distractors, instruction); checker; recorder | Miner node: tickets, submit, attribution, signed serving | Real-arm replay script for a recorded sim episode |
| 3 | Phone controls (touch + tilt) and laptop keyboard; HTTPS tunnel testing | Validator: replay, gate, quality, dedup, scoring, SetWeights (TDD) | LeRobot export of accepted episodes; HF open-sample repo |
| 4 | Verdict screen, leaderboard, "my contributions" | **Testnet deploy**: subnet, open pool + second pool, validator; start the 24 h run | Cold outreach to VLA labs; pitch deck draft |
| 5 | Mobile performance pass; CDN hosting | Load test (~20 phones); failure drills; localnet backup | Demo script rehearsal ×3; fallback recordings |

**Fallback if M0 shows too much drift:** validators re-simulate each short window from the recorded checkpoint and check physical consistency. That still catches forged data, just with a looser success check.

Tracks A, B and C are independent enough to run as parallel AI-agent workstreams, with shared contracts (trajectory schema, seed derivation, API) fixed on day 1.

### Action items for you
- [ ] **Today:** request ~10–20 testnet TAO in the Bittensor Discord (subnet = 1 TAO, plus registrations and validator stake).
- [ ] Have the real SO-101 calibrated with LeRobot on the Mac (follower arm at minimum).
- [ ] Keep one iPhone and one Android phone for testing (iOS tilt sensors need HTTPS + a tap to allow).
- [ ] Pick 10–15 cold-outreach targets (draft message coming on day 4).

---

## 7. Risks (most serious first)
1. **Demand:** no public evidence that buyers pay at scale for browser-sim trajectories. *Mitigation: open sample + cold outreach this week; aim for one reply or quote for the pitch.*
2. **Competition:** Axis has a big head start (funding, 229k users, SN80 relationship). PrismaX and BitRobot are funded.
3. **Emissions dependency:** mainnet costs ~440 TAO to launch; revenue has to arrive before emissions shrink.
4. **Sim-to-real gap:** pure sim is not enough to deploy. SO-101 action-space parity and real-arm replay are the first answer.
5. **Bots and Sybils:** seed binding stops replay and copying, not scripted solvers. Task choice and human-likeness checks carry that load.
6. **Live-demo fragility:** venue Wi-Fi, judges' phone performance, testnet hiccups. Mitigations: CDN, VM, localnet backup, rehearsals.
7. **WASM determinism** (M0 tests it first) and **5-DOF control feel on phones**.
8. **Bittensor 11 is new:** few examples, templates archived.

---

## 8. Phase 2+ (after the hackathon)
- Human-likeness detection on raw input streams.
- **Correction tasks:** a trained policy runs; the human takes over when it fails (highest value for VLA labs).
- Bounty marketplace UI for labs; per-task Demand multipliers wired to payments.
- More robots (ALOHA bimanual, Franka for DROID parity), server-side photorealistic rendering.
- Policy-improvement bonus: periodically fine-tune (e.g. SmolVLA) on each pool's data and reward pools whose data improves held-out success.

---

## 9. Decision log
| # | Question | Decision |
|---|---|---|
| 1 | POC purpose | **Hackathon, ~5 days.** Judged on: working prototype, clear problem/solution, execution, meaningful Bittensor use, credible path forward. Dates set aside. |
| 2 | Who is a miner | **Hybrid pools.** Pro pools recruit and pay humans; we run an open pool paying retail users alpha pro-rata. |
| 3 | Robot | **SO-101** (Menagerie, Apache-2.0). 5-DOF + gripper with position actuators: `shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper`. Export uses LeRobot SO-101 feature names. Notes: no full 6-DOF pose control; ~22 MB of meshes to shrink. |
| 4 | First buyer | **VLA / foundation labs.** Language-conditioned, randomized tasks with a task string per episode and success labels; later correction data. |
| 5 | Chain | **Localnet for dev, testnet for the final demo.** |
| 6 | Real arm | **User owns an SO-101.** Real-arm replay is part of the live demo. |
| 7 | Code reuse | **Forking allowed.** Fork AxisWebInfra with attribution. |
| 8 | Buyer evidence | **Cold outreach this week.** No warm contacts yet. |
| 9 | Demo format | **Live demo only; judges use their own phones.** Requires public HTTPS, CDN hosting and hardening. |
| 10 | Data model | **Open sample + paid full datasets + custom task bounties.** |
| 11 | Team | **User + AI agents.** Parallel tracks A/B/C. |
| — | Data policy | Assumed **human demonstrations only**; enforcement in phase 2. |
| — | Data format | **LeRobotDataset** (lerobot 0.6.1). |
| — | POC task | Assumed **"Put the {color} cube in the {color} bowl"** with distractors; stretch: stacking. |
